# Installation and updates

## Supported starting point

The tested target is **Arch Linux, GNOME 51, Wayland, x86-64**. Use a normal logged-in desktop user. See [compatibility](COMPATIBILITY.md) before trying another environment. There is no AUR, Flatpak, AppImage, Snap or distro package release yet.

## 1. Install dependencies

On Arch, perform a full system update and install the dependencies:

```bash
sudo pacman -Syu --needed git python python-gobject gtk4 libadwaita systemd
```

GNOME installations also need `gnome-shell`, which provides `gnome-extensions`, for extension control. The app can show inventory elsewhere, but GNOME actions do not become available just by installing that executable. Optional milestone audio uses `paplay` and the freedesktop sound theme when present; the app works silently without them.

The relevant Arch package pages are [python-gobject](https://archlinux.org/packages/extra/x86_64/python-gobject/), [gtk4](https://archlinux.org/packages/extra/x86_64/gtk4/) and [libadwaita](https://archlinux.org/packages/extra/x86_64/libadwaita/). Required API versions are listed in [compatibility](COMPATIBILITY.md).

## 2. Obtain version one

### Git checkout

```bash
git clone --branch v1.0.0 https://github.com/Shizzzzoo/memminning.git
cd memminning
```

A tag checkout is detached by design. Create your own branch before making changes, or use `main` for development rather than a fixed release.

### Release archive

Download `memminning-v1.0.0.tar.gz` and `SHA256SUMS` from the [v1.0.0 release](https://github.com/Shizzzzoo/memminning/releases/tag/v1.0.0). In the download directory:

```bash
sha256sum -c SHA256SUMS
tar -xzf memminning-v1.0.0.tar.gz
cd memminning-1.0.0
```

Checksums verify the file against the release's published checksum; they are not an independent signature. The release is not signed.

## 3. Check and install

```bash
/usr/bin/python3 install.py --check
/usr/bin/python3 install.py --with-character-art
```

The check validates Python 3.10+, GTK 4.10+, libadwaita 1.2+ and systemd 254+. It does not prove the session bus, GNOME or memory controller is working; those are checked when scanning/applying actions.

`--with-character-art` explicitly downloads the eight optional game portraits. Every image is verified against the committed SHA-256 manifest. If a source is unavailable or its checksum changes, installation stops before replacing the installed application. Do not disable the checksum check; install without artwork or report the changed source.

For an offline installation, omit the artwork flag:

```bash
/usr/bin/python3 install.py
```

Already-downloaded portraits in the checkout are copied even without the flag. Existing installed portraits are preserved by updates. Without portraits, the app displays generic icons; all resource controls, character names and custom local avatar import still work. A fresh checkout can fetch portraits later:

```bash
/usr/bin/python3 scripts/fetch_character_art.py
/usr/bin/python3 install.py
```

Never run `install.py` as root. No pip installation is needed. In a Conda/virtualenv shell, use the explicit `/usr/bin/python3` shown above.

## 4. Open the application

Choose **Memminning** from the app menu, or:

```bash
~/.local/bin/memminning
```

If `~/.local/bin` is in your shell's PATH, `memminning` also works. Direct development execution is `/usr/bin/python3 run.py`; install first if you want login recovery configured.

## 5. Optional GNOME panel launcher

The installer places the extension under your user GNOME extension directory. On GNOME Wayland, log out and back in so the shell discovers it. Enable **Memminning** in GNOME Extensions, or:

```bash
gnome-extensions enable memminning@local
```

The launcher declares GNOME 51 only. It opens the app; it does not start gaming mode. Do not turn off GNOME version validation to force another version. Panel activation in a fresh GNOME session still needs broader validation.

## Installed files and data

| Path (default) | Purpose |
| --- | --- |
| `~/.local/bin/memminning` | Shell launcher |
| `~/.local/share/memminning/app/` | Application and cached assets |
| `~/.local/share/applications/io.github.memminning.Memminning.desktop` | Application menu entry |
| `~/.config/autostart/io.github.memminning.Recovery.desktop` | Login recovery |
| `~/.local/share/gnome-shell/extensions/memminning@local/` | Optional panel extension |
| `~/.local/state/memminning/` | Recovery journal, logs, preferences and local avatar |

`XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_STATE_HOME` override the corresponding locations. The executable launcher remains under `~/.local/bin`.

## Updating

1. Restore the current session and check that recovery succeeded.
2. Close the GUI.
3. Obtain and review the new release.
4. Run its installer as the same user, with artwork enabled if desired.
5. Reopen Memminning. Existing profile/history and the recovery journal remain outside the application directory.

For a clean Git checkout:

```bash
~/.local/bin/memminning --restore
git fetch --tags
# Replace the example with the release tag you have reviewed.
git switch --detach v1.0.0
/usr/bin/python3 install.py --with-character-art
```

The installer refuses to replace the app while its saved session still requires recovery. No automatic updater or remote-code execution is included.

## Uninstalling

Restore first using the existing installed launcher. Verify the restoration before removing anything. Disable the Memminning panel extension in GNOME Extensions. Remove only the Memminning-specific installed paths listed above, adjusting XDG paths if configured.

Keep `~/.local/state/memminning/` until you have verified recovery. Deleting the recovery journal during a session can leave extensions disabled. User data can be removed later if you no longer want logs/history. Your source checkout is independent of the installed application.
