# Neon Studio

A personal Linux desktop setup with a native settings app, seven desktop widgets, live 1337 logtime, and six original **3840 × 2160 wallpapers** plus **ten anime wallpapers at 4K or higher**.

![Six original 4K wallpapers](wallpapers-preview.jpg)

![Ten included 4K anime wallpapers](anime-wallpapers-preview.jpg)

[Already installed? Follow the upgrade instructions below.](#upgrade-an-existing-installation)

## Install and run

Run these commands in a terminal inside your graphical desktop session:

```bash
cd ~/Desktop
git clone https://github.com/mar1-hh/faklosasd.git
cd faklosasd
bash install.sh
```

HTTPS cloning this public repository does not require a GitHub account or SSH key. If you already use SSH, you can use `git@github.com:mar1-hh/faklosasd.git` as the clone URL instead. The examples assume `~/Desktop/faklosasd`; substitute your checkout's actual path if you installed elsewhere.

**No sudo is used.** The installer checks existing GTK libraries, chooses existing Python interpreters for Requests and the optional pynput helper, creates a user application launcher, starts the cards and enabled keep-awake helper, and opens **Neon Studio**. It does not download system packages or edit your shell startup files.

After installation, search for **Neon Studio** in Applications, or run from the checkout:

```bash
bash open-studio.sh
```

Keep the checkout in place: the launcher points to it. If you move it, rerun `bash install.sh` from its new location. Close the older app/cards before switching from an earlier `~/Desktop/neon-desktop` installation to this checkout.

To install without starting anything now (the default-enabled keep-awake and update-check login entries are still registered):

```bash
bash install.sh --no-start
```

## Automatic update notifications

After installation, Neon Studio checks the public `mar1-hh/faklosasd` **main** branch in the background at graphical login and periodically during the session. Automatic network checks happen **at most once every 24 hours**, including failed attempts. Login and the control panel do not wait for Git or the network. A desktop notification announces each new commit once; open **Neon Studio → Tools → Updates** to see the status. Notifications require `notify-send` and an active desktop notification service; the Tools status works independently.

**Check for updates** runs a fresh background check, so you can retry manually after reconnecting without waiting a day. **Update** is the only action that installs anything. Downloading metadata and notifying never changes the installed source files. Public HTTPS is used for checking/fetching, even for SSH clones, so friends do not need an unlocked SSH agent at login. The configured origin is preserved.

Updates require a clean checkout on `main` whose `origin` points to this repository. Local modifications to tracked files, untracked files other than personal images in `wallpapers/`, another branch/remote, an unfinished Git operation, or ahead/diverged commits block installation with an explanation. Commit or move your own changes and reconcile Git history yourself; the app never stashes, resets, forces a checkout, or overwrites those edits. If main changes after your check, check again before installing.

The updater fetches the reviewed commit and uses a fast-forward-only merge. It rejects incoming private-data paths and collisions with ignored files. It takes a private backup under `state/updater/backups/`, preserves `state/preferences.json`, notes, custom wallpapers, caches, credentials and interpreter pins, and runs `bash install.sh --no-start` to refresh user launchers/startup entries. This registration-only installer uses existing dependencies; it does not install packages or require sudo. Existing external wallpaper folders and user credentials/configuration are left in place.

Only this checkout's running cards and managed keep-awake helper are stopped and restarted; stopped cards stay stopped, and an active keep-awake session retains its remaining duration. The update watcher restarts, and an open control panel reopens with the new code. Settings controls are temporarily disabled; notes still in the editor are saved first. Finish wallpaper downloads/imports before clicking Update. Other checkouts and unrelated processes are not stopped. Cross-process locks prevent overlapping operations, and Git/network/installer commands have timeouts.

If installation fails after Git advances, personal files are restored from the snapshot and the app reports the failure. **Check for updates → Update** retries installation when the code is already current. Git is never rolled back automatically. Keep the backup until you have confirmed the app works. See `state/updates.log` for updater-process output, `state/updater/install.log` for installer diagnostics, and `state/updater/status.json` for the last result. Backups are retained; you can remove older backup folders after confirming an update works to reclaim disk space. A forced shutdown during installation can require rerunning `bash install.sh` manually; backups remain available. New features requiring additional dependencies may need a manual dependency install before retrying.

Checks use the user startup entry `~/.config/autostart/neon-updates.desktop` (or your `XDG_CONFIG_HOME` equivalent), with no system service and no sudo. `bash uninstall.sh` stops this checkout's watcher and removes its startup entry, while preserving personal files. Finish any running update before uninstalling.

## Upgrade an existing installation

**One-time manual step for existing users:** older versions cannot discover this feature themselves. Run the commands below once to install the updater and its login entry. Afterward use **Tools → Updates** for routine upgrades; you do not need to send friends commands whenever main changes.

Use these steps if you or your friends already cloned this repository. Your widget settings, imported wallpapers, notes, logtime cache and restore snapshots stay in the Git-ignored `state/` folder.

1. **Close the Neon Studio control-panel window first.** The desktop cards can remain until the restart step stops them. Closing the window lets the next launch load the new app code.
2. Run:

   ```bash
   cd ~/Desktop/faklosasd
   git pull --ff-only
   /usr/bin/python3 -c 'from keep_awake import stop; print(stop())'
   bash restart-widgets.sh
   ```

   The keep-awake command stops its current process without changing your saved on/off choice. The restart script stops this checkout's cards, reruns installation, refreshes launchers/interpreter paths, migrates an enabled older Neon login entry, and opens the updated app. It starts keep awake again only if your preference is enabled.
3. In **Widgets**, confirm **Start cards when I log in** and **Keep awake at login** match your choices. Card startup remains opt-in; keep awake defaults to on only when no explicit choice was saved.

Routine updates take effect after restarting the processes; a logout is only needed when GNOME first loads the personal wallpaper profile. Keep using the same checkout, so the existing `state/` folder stays attached to your installation. The optional example configuration replaces preferences and is intended for a deliberate reset, not a normal upgrade.

If `git pull --ff-only` reports local source changes or diverged history, stop and preserve those edits before continuing. Your personal `state/` files are ignored by Git and do not need to be discarded for an update.

### Moving from the old `neon-desktop` folder

If your old widgets run from `~/Desktop/neon-desktop`, close the old control panel and stop those cards first:

```bash
cd ~/Desktop/neon-desktop
/usr/bin/python3 -c 'from studio_backend import stop_widgets; print(stop_widgets())'
```

Then use the fresh-install commands above if you have not cloned `faklosasd`, or the existing-repository upgrade commands if you already have that checkout. Run installation from **the repository folder**; running scripts in `neon-desktop` continues to use the old code.

The installer retargets an existing **enabled** Neon card login entry to this checkout. A disabled entry stays disabled. It also refreshes the Applications launcher and replaces the marked standalone `sc.py` startup entry with the app-controlled helper. Existing enabled login startup therefore follows the new repository on your next login.

For a one-time switch of just the widget login target, run:

```bash
/usr/bin/python3 ~/Desktop/faklosasd/install-dashboard.py
```

To retain preferences when moving folders, copy `state/preferences.json` from the old installation **before the first launch of the new one**, provided the new checkout has no preferences you want to keep. You can bring old custom images into the new version with **Wallpapers → Add to collection…**. Keep the old folder until you have imported anything you need and applied a wallpaper from the new collection, since the desktop may still refer to an old image's path.

## Requirements

The main target is **Ubuntu 22.04, GNOME 42, X11**. The control panel uses GTK 4 and libadwaita; desktop cards run separately with GTK 3. Other GNOME releases may work but have not been visually verified. Wayland can restrict desktop positioning and dragging.

Required on the machine:

- Git for update checks and fast-forward installation; `notify-send` (libnotify) for update notifications.
- `/usr/bin/python3` with PyGObject (`gi`), GTK 3, GTK 4, libadwaita 1 and GdkPixbuf/SVG support.
- A Python 3 interpreter with `requests` for logtime; it can differ from the GUI interpreter.
- GNOME's `gsettings`, user `systemctl`, and standard `pgrep` tools.
- An active GNOME Shell user service for personal-profile wallpaper changes.

The campus workstation used for development already had the GTK prerequisites. The installer reports missing libraries instead of attempting a privileged installation. Keep awake requires a Python interpreter with `pynput`; its interpreter is selected separately from the GUI and logtime interpreter.

If only Requests is missing, use a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
NEON_LOGTIME_PYTHON="$PWD/.venv/bin/python" bash install.sh
```

## Use the app

- **Wallpapers:** browse all 16 included scenes, select an additional folder, or use **Add to collection…** to import one or several images. Imports are copied into `state/wallpapers/`, stay in the gallery even if the originals are moved, and remain Git-ignored. Duplicate content is reused; conflicting filenames are kept as separate numbered files. **Open image…** is available for a temporary preview without importing.
- **Appearance:** automatically match the applied wallpaper’s dominant meaningful hue, or choose a fixed Rose, Violet, Teal, Amber or Blue preset; change widget size (80–180%), opacity, screen margin, and clock seconds. Optionally match GNOME Terminal colors and transparency too. Changes save automatically.
- **Widgets:** toggle Logtime, Quick links, Clock, System monitor, Calendar, Notes and App launcher independently. Enable **Arrange widgets**, drag a card by its title/empty area, then disable Arrange to put cards behind normal windows. Notes are editable here.
- **Logtime:** set your 1337 username and target, inspect the active period, or refresh the API reading.
- **Tools:** start/stop cards, view diagnostics, restore saved widget/background settings, and disable the personal wallpaper setup.

Closing the control panel leaves the desktop cards running. Browser and app launches are asynchronous so they do not block the live clock/logtime.

### Start at login

Enable **Widgets → Start cards when I log in**. Card login startup is opt-in. The separate **Keep awake at login** feature is enabled by default. Disable the same switch to stop future automatic launches.

### Use the appearance settings from this setup

`config.example.json` contains the shareable appearance choices from the original setup, with machine paths and account details removed. It is optional; a fresh install otherwise uses the app defaults.

Before first installation, or after stopping the cards:

```bash
mkdir -p state
cp config.example.json state/preferences.json
bash install.sh
```

Copying this file replaces your saved widget preferences. It includes the larger widget size, opacity, margin, clock-seconds choice and card visibility. The wallpaper folder and username resolve locally.

## Apply a wallpaper

1. Open **Wallpapers** in Neon Studio.
2. Select a scene or use **Open image…** / **Change folder…**.
3. Click the wallpaper thumbnail. It applies immediately; **Reapply selected** is only a fallback.
4. If the app says the image was saved but the profile is pending, **log out and back in once**. Later wallpaper changes should be immediate.

The one-time logout lets GNOME Shell load the personal dconf profile. The app never forcibly restarts Shell. A campus that permits the TrpStrata-style personal-profile setup is required for this mode.

The setup writes only user-owned configuration:

```text
~/.config/dconf/neon-studio-wallpaper.profile
~/.config/systemd/user/org.gnome.Shell@x11.service.d/90-neon-studio-wallpaper.conf
```

A Wayland session uses its corresponding Shell unit. The personal profile selects the user settings database rather than the usual campus database stack, which also affects which managed defaults/locks Shell reads. Use this mode only where that session configuration is permitted. Existing conflicting profile overrides are preserved and reported.

The first wallpaper change backs up the previous background. Failed writes roll back completed changes. **Tools → Restore previous wallpaper** restores the saved image. **Tools → Disable personal wallpaper setup**, followed by logout/login, returns Shell to its previous profile selection. The inactive profile file is retained until after the running session can stop using it.

## Logtime

The original tracker is bundled as `logtime-core.py`; no separate Desktop script is needed. Set the username under **Logtime** or leave it blank to detect your Linux username. The default goal is 120 hours.

- A period runs from the 28th through the following 27th.
- The display is **projected hours**: API period total plus the active session, counting in `HH:MM:SS`.
- API requests refresh every five minutes, outside the graphical event loop, with verified TLS and caching.
- If `who` detects no login, the helper checks graphical logind sessions, then uses the GNOME Shell process age as a labelled estimate.
- If no session can be found, only the API total is shown. Confirmed campus credit can differ from the live estimate.

To diagnose logtime from the checkout after installation:

```bash
./python logtime-widget.py
```

The original script's `LOGTIME_API_URL`, `LOGTIME_TIMEOUT`, `LOGTIME_TARGET_HOURS` and other environment options remain available. This feature requires access to the configured campus API.

## Stop, restart, and update

**Tools → Stop desktop cards** stops them without closing the app.

From the checkout:

```bash
/usr/bin/python3 -c 'from studio_backend import stop_widgets; print(stop_widgets())'
```

Reload updated widget code:

```bash
bash restart-widgets.sh
```

Update this checkout:

```bash
git pull --ff-only
```

Close Neon Studio and run `bash restart-widgets.sh` afterward. Your private runtime settings are ignored by Git and stay local.

## Restore or uninstall

Use the restore buttons in **Tools** for individual changes. To remove the app launcher, login entry and this project's Shell override, and stop the cards:

```bash
bash uninstall.sh
```

Close any open control-panel window first. If the personal profile was enabled, log out/in after removal. The checkout, wallpaper collection and local backups remain on disk. Only launchers and overrides owned by this setup are removed; conflicting/unrelated files are preserved.

## Troubleshooting

**The app does not appear:** run `bash open-studio.sh` in a normal desktop terminal to see the error. Read `state/studio.log` for installer-launched errors.

**No cards or a card disappears:** check **Tools → Diagnostics**, visibility switches and whether Arrange is enabled. Desktop cards normally sit behind other app windows. Read `state/widgets.log`.

**Cards overlap at startup:** this version recalculates positions after GTK finishes sizing them. If you have previously saved overlapping drag positions, use **Widgets → Reset card positions**. The chosen size is preserved.

**Wallpaper saved but unchanged:** complete the one-time logout/login. If it still fails, check **Tools → Diagnostics**. An active GNOME Shell user service is required; conflicting profile overrides are reported rather than overwritten.

**42 Intra does not open:** check your default browser and connection. Failed or timed-out launches display a message under Quick links; live widget updates continue.

**Logtime is unavailable:** verify your username, API access and interpreter. Run `./python logtime-widget.py` and check `state/logtime.log`.

## Development and files

```text
control-center.py      GTK 4/libadwaita settings app
desktop-widgets.py     GTK 3 desktop cards and live layout
dashboard.py           Shared card content
native_wallpaper.py    Personal-profile setup, verification and undo
logtime-widget.py      Adapter around the supplied tracker
preferences.py         Validated preferences and atomic saves
external_actions.py    Asynchronous website/application launching
wallpapers/            16 wallpapers, original SVG sources and anime source manifest
config.example.json    Portable example appearance settings
tests/                 Headless regression tests
state/                 Private imports, settings, API cache, logs and backups (Git-ignored)
```

Legacy `extension/` and `configure.py` are retained for compatibility with the original prototype. Normal installation uses the standalone cards, not a GNOME extension.

Run checks from the repository root:

```bash
GSETTINGS_BACKEND=memory /usr/bin/python3 -m unittest discover -s tests -v
bash -n install.sh restart-widgets.sh uninstall.sh open-studio.sh
```

These check preferences, restore snapshots, wallpaper transactions and profile setup, missing optional apps, asynchronous launch failures/timeouts, live counting, widget placement, launchers and autostart ownership. Actual desktop rendering, browser launch and campus API behavior need verification in a graphical session.

Code and original assets are MIT licensed. The downloaded anime artwork belongs to its respective creators; source URLs and actual dimensions are recorded in [wallpapers/SOURCES.json](wallpapers/SOURCES.json). See [LICENSE](LICENSE) and [THIRD_PARTY.md](THIRD_PARTY.md). No personal logs, API responses, saved wallpaper backups, account names, interpreter symlinks or absolute user paths are published.


### Wallpaper colors and centered cards

**Automatically match wallpaper** is enabled by default. Click a wallpaper to apply it and extract its strongest meaningful hue: near-black backgrounds and transparent pixels are ignored, and neighboring hues are grouped rather than averaging unrelated colors together. That hue colors card numbers, headings, borders, progress, buttons and a dark tinted surface. The accent is adjusted for legibility. The current hex value is shown in Appearance. Choosing a fixed preset disables automatic matching; the switch or Match widget accent button turns it back on. Widget text and calendar/app-launcher content are centered within their cards.

All ten added anime wallpapers were checked from their actual file headers: eight are 3840×2160, one is 3840×2400, and one is 4500×2247. None was upscaled. Three downloaded WebP files were decoded to lossless PNG at their original dimensions for compatibility with this workstation’s image loaders. The original six landscapes remain included.


### Monster, Mushoku Tensei, Naruto and Orb pack

The app now downloads one sourced wallpaper for each requested series in the background when it opens: **Monster (Johan Liebert)**, **Mushoku Tensei: Jobless Reincarnation**, **Naruto (Rasengan)**, and **Orb: On the Movements of the Earth (Rafal)**. Their original pages and advertised dimensions are listed in [wallpapers/ANIME_PACK.json](wallpapers/ANIME_PACK.json).

These four files are fetched into the private, Git-ignored `state/wallpapers/` collection on your own machine. They are not falsely represented as already bundled downloads. The app validates the returned image, decodes it, and verifies at least 3840×2160 before adding it. It does not upscale a smaller preview or save an HTML error as an image. Completed files are cached; unavailable sources have retry and source-page controls on the Wallpapers page. You can also run `/usr/bin/python3 anime_pack.py` from the checkout to download without opening the control panel.

The tool session used to prepare this update cannot directly download from those image hosts, so live download availability still needs checking in your desktop session. Ordinary app operations stay responsive while the pack downloads. No login details, cookies, privileged commands, or Wallpaper Engine installation are needed.

### One-click wallpaper selection and transparent calendar days

Clicking a gallery thumbnail now applies that exact image and its automatic accent. Rapid clicks are debounced so the last choice wins. Startup/gallery refreshes only preview an image and never replace your background on their own. Selected/applied tiles have distinct outlines; failures retain the existing wallpaper and show an explanation. The one-time personal-profile login requirement is unchanged.

The GTK calendar's day grid, header and selected-day background are transparent. The card surface remains, and selected dates use the current accent color rather than a filled rectangle. Restart the cards once to load the new styling.


## Keep awake — built-in sc.py feature

The app now bundles the behavior of your supplied `sc.py`. **Widgets → Keep awake at login** is **on by default** for new and existing settings that have no saved choice. Its original behavior is preserved: a brief Shift press/release every 30 seconds for up to 60 minutes per login. Those events go to the focused application, as in the original script.

Run `bash install.sh` once after updating. The installer finds a Python with `pynput`, pins its absolute path in the Git-ignored `keep-awake-python` symlink, and adds `~/.config/autostart/neon-keep-awake.desktop` with zero added login delay. Normal installation starts a run now; `--no-start` registers it for the next login without starting it now. The helper is independent of whether the cards themselves start at login.

Turning the switch **off** stops the current helper, releases Shift as cleanup, and removes its login entry. Turning it **on** starts a new 60-minute run and enables future login startup. Your off choice survives updates and reinstalling. Closing Neon Studio or stopping the desktop cards leaves this separate helper running until its duration expires; use its own switch to stop it. Its status label distinguishes running, off, completed and dependency errors.

No duplicate helper instances are allowed. If you installed the earlier standalone `sc-login` startup entry, the app installer backs up and replaces only that marked entry, stopping the known old Desktop script before starting the bundled version. Your original `~/Desktop/sc.py` is left unchanged, and the app no longer depends on that external file.

If no installed interpreter contains pynput, the rest of the app still installs and reports the missing keep-awake dependency. Install it into your own virtual environment if needed:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-keep-awake.txt
NEON_LOGTIME_PYTHON="$PWD/.venv/bin/python" NEON_KEEP_AWAKE_PYTHON="$PWD/.venv/bin/python" bash install.sh
```

The helper uses pynput's X11 keyboard backend on the target campus desktop; Wayland may restrict synthetic keyboard events. It does not change system power/lock policies or use sudo.

Logs and status remain private in `state/keep-awake.log`, `state/keep-awake-status.json`, and `state/keep-awake.pid`. The helper checks the enabled preference at least once per second and handles termination with a best-effort Shift release. `uninstall.sh` stops it and removes only its owned login entry.

Regression tests use a fake keyboard/controller and clock; they never send actual key events.


## Transparent, wallpaper-matched GNOME Terminal

1. Open **Appearance → GNOME Terminal** in Neon Studio.
2. Turn on **Match terminal to wallpaper**. This feature is opt-in.
3. Adjust **Background transparency (%)**: `0` is solid, `100` is fully transparent. The default is `25`.
4. Click another wallpaper or choose a widget accent; the terminal follows the same accent and dark card surface automatically while the control panel is running.

The default **GNOME Terminal profile** gets a matching dark background, readable foreground, accent-colored cursor/selection and a 16-color ANSI palette that keeps red/green/yellow semantics. Windows using that profile update live; other profiles and terminal applications keep their own settings. The app does not change the terminal font, shell command, shortcuts or default profile selection.

Ubuntu's patched GNOME Terminal on the target workstation supports `use-transparent-background`, `use-theme-transparency` and `background-transparency-percent`. Other builds may omit those keys: colors still work, the transparency slider is disabled, and the status explains the limitation. Compositor support is required to see background transparency.

Before changing any profile, its original color/opacity overrides are saved privately in `state/terminal-before.json`. Turning the switch off, clicking **Restore original terminal**, or uninstalling restores those values (including settings that were previously unset and inherited their defaults). Administrator-locked terminal keys are reported without bypassing them. **Apply / retry terminal theme** retries after a settings service or profile change.

To restore from the checkout without opening the GUI:

```bash
/usr/bin/python3 terminal_theme.py restore
```

Close the old control-panel window and run `bash restart-widgets.sh` once after updating, then enable the option in Appearance. The tests use fake profiles and GNOME's memory backend; they do not recolor the test runner's live terminal.

## Pomodoro and refreshed desktop cards

The desktop cards retain your saved opacity and wallpaper-tinted surfaces. Cyan highlights, brighter text, compact controls and consistent spacing improve readability. Logtime shows accumulated hours/minutes against the target, completion and remaining hours; the active session retains seconds. Quick Links sit in one row, System includes a memory bar, and the calendar marks today while dimming adjacent-month dates.

Enable **Pomodoro** in **Widgets**. Its default location is below Quick Links; it searches for free space if that column is full. Use **Arrange widgets** to move it and save its position. Very small displays or large widget scales may require reducing scale or hiding cards to fit everything.

Choose Focus, Short or Long, then **Start**. **Pause** preserves remaining time; **Reset** restores the selected mode's duration; **Skip** moves on without crediting a focus session. Four completed focus sessions offer a long break. The four dots track the current cycle. Completing or skipping a long break begins a new cycle.

Under **Appearance → Pomodoro**, set durations (defaults 25/5/15 minutes), notifications, sound and optional automatic next-session startup. Duration changes apply at Reset or the next session. Manual startup is the default. Focus is cyan; breaks are green. Notifications use existing `notify-send`; sound uses `paplay` and the system completion sound when available. Missing optional tools do not interrupt the timer.

Timer state is stored privately in `state/pomodoro.json`. A running timer uses a deadline, survives widget restarts, and handles a late completion once. With auto-start, the next session begins when the completion is processed; missed unattended cycles are not credited. Hiding the card does not reset or pause it. Completion is saved before alerts are sent, preventing repeat alerts after a restart; an abrupt crash between saving and alert delivery can suppress that alert.

To try the changes, close the settings window, run `bash restart-widgets.sh`, then open Appearance and Widgets. Start/Pause/Reset/Skip the timer, enable a one-minute focus duration and Reset to test completion, and restart the widgets while the timer is running to verify recovery. Check the calendar, links and logtime alongside it. No sudo or additional Python packages are needed.

### Personal wallpapers and updates

Use **Wallpapers → Add to collection…** for personal images. These imports live in Git-ignored `state/wallpapers/` and do not block updates. Images copied directly into `wallpapers/` are also allowed by the updater when they are untracked regular PNG, JPEG, WebP or BMP files. They are backed up and preserved. Code files, staged changes, edits to bundled images, and divergent local commits still require manual attention.

If an incoming bundled image uses the same path as your personal wallpaper, the updater stops before changing files. Import your image through **Add to collection…**, apply the imported copy, then move the original out of the repository and retry. No image is automatically deleted or overwritten.

**Friends running an older updater:** import and apply their custom images through **Add to collection…**, then move only the original untracked images from `wallpapers/` to a folder outside the repository. The old updater can then install this fix using **Check for updates → Update**. Keep the originals until the imported copies are confirmed. If the message mentions modified tracked files or divergent commits, preserve that work and resolve the Git changes separately; do not reset or force-push to fix a wallpaper collection.
