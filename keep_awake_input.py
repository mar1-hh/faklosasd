"""Multi-mode keep-awake input controller for Neon Studio.

Supported modes:
1. 'inhibit': Native GNOME session idle inhibitor over D-Bus (zero typing/mouse interference).
2. 'mouse': GNOME session inhibitor + safe XTEST pointer round trip (moves to origin and restores instantly).
   Skipped automatically if any keyboard keys or mouse buttons are held.
3. 'shift': Legacy synthetic Shift press/release via XTEST (compatibility fallback).
"""
import ctypes as C
import os


class GnomeInhibitor:
    """Holds an active idle inhibitor via org.gnome.SessionManager D-Bus."""

    def __init__(self):
        self.cookie = None
        self.bus = None
        try:
            from gi.repository import Gio, GLib
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            reply = self.bus.call_sync(
                "org.gnome.SessionManager",
                "/org/gnome/SessionManager",
                "org.gnome.SessionManager",
                "Inhibit",
                GLib.Variant("(susu)", ("Neon Studio", 0, "Desktop Keep Awake", 8)),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
            self.cookie = reply.unpack()[0]
        except Exception:
            self.cookie = None

    def close(self):
        if self.cookie is not None and self.bus is not None:
            try:
                from gi.repository import GLib, Gio
                self.bus.call_sync(
                    "org.gnome.SessionManager",
                    "/org/gnome/SessionManager",
                    "org.gnome.SessionManager",
                    "Uninhibit",
                    GLib.Variant("(u)", (self.cookie,)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    1500,
                    None,
                )
            except Exception:
                pass
            self.cookie = None


class X11Pointer:
    """Safe XTEST pointer round trip with held-key and held-button suppression."""

    def __init__(self, loader=C.CDLL):
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            raise RuntimeError("Synthetic pointer movement requires an X11 session.")
        try:
            self.x = loader("libX11.so.6")
            self.xt = loader("libXtst.so.6")
        except OSError as exc:
            raise RuntimeError("Pointer keep-awake requires libX11.so.6 and libXtst.so.6.") from exc

        self.x.XOpenDisplay.argtypes = [C.c_char_p]
        self.x.XOpenDisplay.restype = C.c_void_p
        self.x.XDefaultScreen.argtypes = [C.c_void_p]
        self.x.XDefaultScreen.restype = C.c_int
        self.x.XRootWindow.argtypes = [C.c_void_p, C.c_int]
        self.x.XRootWindow.restype = C.c_ulong
        self.x.XQueryPointer.argtypes = [
            C.c_void_p,
            C.c_ulong,
            C.POINTER(C.c_ulong),
            C.POINTER(C.c_ulong),
            C.POINTER(C.c_int),
            C.POINTER(C.c_int),
            C.POINTER(C.c_int),
            C.POINTER(C.c_int),
            C.POINTER(C.c_uint),
        ]
        self.x.XQueryPointer.restype = C.c_int
        self.x.XQueryKeymap.argtypes = [C.c_void_p, C.c_char_p]
        self.x.XQueryKeymap.restype = C.c_int
        self.x.XSync.argtypes = [C.c_void_p, C.c_int]
        self.x.XSync.restype = C.c_int
        self.x.XCloseDisplay.argtypes = [C.c_void_p]
        self.x.XCloseDisplay.restype = C.c_int

        self.xt.XTestQueryExtension.argtypes = [C.c_void_p] + [C.POINTER(C.c_int)] * 4
        self.xt.XTestQueryExtension.restype = C.c_int
        self.xt.XTestFakeMotionEvent.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_ulong]
        self.xt.XTestFakeMotionEvent.restype = C.c_int

        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Failed to acquire X11 display connection.")
        outputs = [C.c_int() for _ in range(4)]
        if not self.xt.XTestQueryExtension(self.display, *[C.byref(v) for v in outputs]):
            self.close()
            raise RuntimeError("XTest extension is not available on this X server.")
        self.screen = self.x.XDefaultScreen(self.display)
        self.root = self.x.XRootWindow(self.display, self.screen)

    def pulse(self):
        """Perform a single round trip to origin and back; skips if user is interacting."""
        if not self.display:
            return False

        # 1. Skip if any key on the keyboard is currently pressed
        keybuf = C.create_string_buffer(32)
        if not self.x.XQueryKeymap(self.display, keybuf) or any(keybuf.raw):
            return False

        # 2. Skip if any mouse buttons (Button1Mask .. Button5Mask = 0x1F00) are held
        r_root, r_child = C.c_ulong(), C.c_ulong()
        rx, ry, wx, wy = C.c_int(), C.c_int(), C.c_int(), C.c_int()
        mask = C.c_uint()
        if not self.x.XQueryPointer(
            self.display,
            self.root,
            C.byref(r_root),
            C.byref(r_child),
            C.byref(rx),
            C.byref(ry),
            C.byref(wx),
            C.byref(wy),
            C.byref(mask),
        ):
            return False
        if mask.value & 0x1F00:
            return False

        orig_x, orig_y = rx.value, ry.value
        target_x = 1 if (orig_x == 0 and orig_y == 0) else 0

        # Move to target and immediately restore
        try:
            self.xt.XTestFakeMotionEvent(self.display, self.screen, target_x, 0, 0)
        finally:
            self.xt.XTestFakeMotionEvent(self.display, self.screen, orig_x, orig_y, 0)
            self.x.XSync(self.display, 0)
        return True

    def close(self):
        if hasattr(self, "display") and self.display:
            self.x.XCloseDisplay(self.display)
            self.display = None


class X11Keyboard:
    """Legacy X11 Shift controller."""

    def __init__(self, loader=C.CDLL):
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            raise RuntimeError("Keep awake requires an X11 session.")
        try:
            self.x = loader("libX11.so.6")
            self.xt = loader("libXtst.so.6")
        except OSError as exc:
            raise RuntimeError("Keep awake requires libX11 and libXtst libraries.") from exc

        def bind(lib, name, args, result):
            fn = getattr(lib, name)
            fn.argtypes = args
            fn.restype = result

        bind(self.x, "XOpenDisplay", [C.c_char_p], C.c_void_p)
        bind(self.x, "XCloseDisplay", [C.c_void_p], C.c_int)
        bind(self.x, "XStringToKeysym", [C.c_char_p], C.c_ulong)
        bind(self.x, "XKeysymToKeycode", [C.c_void_p, C.c_ulong], C.c_ubyte)
        bind(self.x, "XQueryKeymap", [C.c_void_p, C.c_void_p], C.c_int)
        bind(self.x, "XFlush", [C.c_void_p], C.c_int)
        bind(self.xt, "XTestQueryExtension", [C.c_void_p] + [C.POINTER(C.c_int)] * 4, C.c_int)
        bind(self.xt, "XTestFakeKeyEvent", [C.c_void_p, C.c_uint, C.c_int, C.c_ulong], C.c_int)

        self.display = self.x.XOpenDisplay(None)
        self.pressed = False
        if not self.display:
            raise RuntimeError("Failed to acquire X connection for an active desktop session.")
        try:
            outputs = [C.c_int() for _ in range(4)]
            if not self.xt.XTestQueryExtension(self.display, *[C.byref(v) for v in outputs]):
                raise RuntimeError("The X11 server does not provide XTest input support.")
            self.keycode = self.x.XKeysymToKeycode(self.display, self.x.XStringToKeysym(b"Shift_L"))
            if not self.keycode:
                raise RuntimeError("The X11 keyboard has no Shift key mapping.")
        except Exception:
            self.close()
            raise

    def press(self, key="shift"):
        keys = C.create_string_buffer(32)
        self.x.XQueryKeymap(self.display, keys)
        if keys.raw[self.keycode // 8] & (1 << (self.keycode % 8)):
            return
        if not self.xt.XTestFakeKeyEvent(self.display, self.keycode, 1, 0):
            raise RuntimeError("X11 rejected the keep-awake key event.")
        self.pressed = True
        self.x.XFlush(self.display)

    def release(self, key="shift"):
        if self.display and self.pressed:
            if not self.xt.XTestFakeKeyEvent(self.display, self.keycode, 0, 0):
                raise RuntimeError("X11 rejected the Shift release.")
            self.x.XFlush(self.display)
            self.pressed = False

    def pulse(self):
        try:
            self.press("shift")
        finally:
            self.release("shift")

    def close(self):
        if getattr(self, "display", None):
            try:
                self.release("shift")
            finally:
                self.x.XCloseDisplay(self.display)
                self.display = None


class KeepAwakeController:
    """Unified Keep-Awake controller supporting 'inhibit', 'mouse', and 'shift'."""

    def __init__(self, mode="mouse"):
        self.mode = mode if mode in ("inhibit", "mouse", "shift") else "mouse"
        self.inhibitor = GnomeInhibitor()
        self.input_backend = None

        if self.mode == "mouse":
            try:
                self.input_backend = X11Pointer()
            except Exception:
                # If pointer mode fails, fallback to pure inhibit
                self.input_backend = None
        elif self.mode == "shift":
            try:
                self.input_backend = X11Keyboard()
            except Exception:
                self.input_backend = None

    def pulse(self):
        if self.input_backend and hasattr(self.input_backend, "pulse"):
            return self.input_backend.pulse()
        return True

    def press(self, key="shift"):
        if self.input_backend and hasattr(self.input_backend, "press"):
            self.input_backend.press(key)

    def release(self, key="shift"):
        if self.input_backend and hasattr(self.input_backend, "release"):
            self.input_backend.release(key)

    def close(self):
        if self.inhibitor:
            self.inhibitor.close()
        if self.input_backend:
            self.input_backend.close()
