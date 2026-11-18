"""Minimal X11 Shift controller using libraries already present on GNOME desktops."""
import ctypes as C
import os

class X11Keyboard:
 def __init__(self,loader=C.CDLL):
  if os.environ.get('XDG_SESSION_TYPE')=='wayland':
   raise RuntimeError('Keep awake requires an X11 session; synthetic Shift events are not supported on Wayland.')
  try:self.x=loader('libX11.so.6');self.xt=loader('libXtst.so.6')
  except OSError as error:raise RuntimeError('Keep awake needs the system X11 and XTest libraries (libX11 and libXtst).') from error
  def bind(lib,name,args,result):
   function=getattr(lib,name);function.argtypes=args;function.restype=result
  bind(self.x,'XOpenDisplay',[C.c_char_p],C.c_void_p)
  bind(self.x,'XCloseDisplay',[C.c_void_p],C.c_int)
  bind(self.x,'XStringToKeysym',[C.c_char_p],C.c_ulong)
  bind(self.x,'XKeysymToKeycode',[C.c_void_p,C.c_ulong],C.c_ubyte)
  bind(self.x,'XQueryKeymap',[C.c_void_p,C.c_void_p],C.c_int)
  bind(self.x,'XFlush',[C.c_void_p],C.c_int)
  bind(self.xt,'XTestQueryExtension',[C.c_void_p]+[C.POINTER(C.c_int)]*4,C.c_int)
  bind(self.xt,'XTestFakeKeyEvent',[C.c_void_p,C.c_uint,C.c_int,C.c_ulong],C.c_int)
  self.display=self.x.XOpenDisplay(None);self.pressed=False
  if not self.display:raise RuntimeError('Failed to acquire X connection. Open Neon Studio from Applications in your active desktop session.')
  try:
   outputs=[C.c_int() for _ in range(4)]
   if not self.xt.XTestQueryExtension(self.display,*[C.byref(v) for v in outputs]):raise RuntimeError('The X11 server does not provide XTest input support.')
   self.keycode=self.x.XKeysymToKeycode(self.display,self.x.XStringToKeysym(b'Shift_L'))
   if not self.keycode:raise RuntimeError('The X11 keyboard has no Shift key mapping.')
  except Exception:self.close();raise
 def press(self,key):
  keys=C.create_string_buffer(32);self.x.XQueryKeymap(self.display,keys)
  if keys.raw[self.keycode//8] & (1 << (self.keycode%8)):return
  if not self.xt.XTestFakeKeyEvent(self.display,self.keycode,1,0):raise RuntimeError('X11 rejected the keep-awake key event.')
  self.pressed=True;self.x.XFlush(self.display)
 def release(self,key):
  if self.display and self.pressed:
   if not self.xt.XTestFakeKeyEvent(self.display,self.keycode,0,0):raise RuntimeError('X11 rejected the Shift release.')
   self.x.XFlush(self.display);self.pressed=False
 def close(self):
  if self.display:
   try:self.release('shift')
   finally:self.x.XCloseDisplay(self.display);self.display=None
