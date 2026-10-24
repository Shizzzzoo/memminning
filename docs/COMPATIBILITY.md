# Devices, desktops and compatibility

## What has actually been tested

The development system is an **x86-64 Arch Linux desktop, GNOME Shell 51.1, Wayland, Linux 6.18.55-1-lts**, with Python 3.14.8, GTK 4.24, libadwaita 1.10 and systemd 262. It has approximately 8 GB of physical RAM.

Validation includes unit tests, real GTK rendering, GUI interactions against simulated targets, a read-only live system scan, and a real systemd restoration timer using an empty isolated session. It does **not** establish that every extension, real background service, machine or failure mode is safe. Live destructive/failure scenarios and fresh-login panel activation need further disposable-environment testing.

CI's Python and virtual-display jobs exercise code portability and UI behavior; a passing CI run does not certify the runner's distribution for live resource control.

## Software requirements

| Component | Requirement | Reason |
| --- | --- | --- |
| Python | 3.10+ | Type syntax and Linux OS-release discovery |
| PyGObject | Distribution package exposing Gtk 4 / Adw 1 | Native bindings |
| GTK | 4.10+ | [Gtk.FileDialog](https://docs.gtk.org/gtk4/class.FileDialog.html) for avatar import |
| libadwaita | 1.2+ | [Adw.MessageDialog](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.MessageDialog.html), application shell and toasts |
| systemd | 254+ | Restoration command uses `systemd-run --expand-environment=no` |
| User session | Working user systemd manager and session D-Bus | Service actions, timers and GNOME operations |
| cgroups | v2 with a usable memory controller | Soft memory limits |
| GNOME integration | Active GNOME session and `gnome-extensions` | Live extension discovery/control |
| GNOME panel launcher | Shell 51 | Only version declared in metadata |

`install.py --check` checks installed software, not every runtime/session condition. Components can exist while session access is blocked, especially in containers, SSH sessions and application sandboxes.

## Device support

| Device/platform | Status | Notes |
| --- | --- | --- |
| Intel/AMD x86-64 Linux desktops and laptops | Tested on one Arch/GNOME system | No CPU-vendor-specific code; additional configurations remain unvalidated |
| ARM64 PCs, SBCs, Raspberry Pi | Untested | Python source is architecture-independent, but compatible GTK/systemd/desktop packages and testing are still needed |
| Steam Deck / SteamOS | Not supported as a validated release target | No immutable-system installer, controller UI or Gaming Mode integration; KDE discovery alone does not establish device support |
| Virtual machines | Untested | Scans describe the guest, not host RAM/processes |
| Headless servers / SSH-only shells | GUI unavailable | CLI needs accessible session services for user actions; root/system services are never a supported control target |
| Windows / macOS / mobile platforms | Unsupported | Linux `/proc`, systemd and desktop integrations are required |
| Non-systemd Linux | Unsupported | No alternative restore scheduler is implemented |

No GPU vendor is specifically supported for tuning. The app does not control GPU clocks, VRAM, drivers, game graphics or anti-cheat. Character portraits are cosmetic and do not indicate that Fortnite, VALORANT or another game can run on a given device.

A mouse/keyboard desktop around **1280×900 or larger** is recommended for comfortable use. Scrolling is provided for smaller windows, but mobile/controller-first layouts have not been designed. There is no benchmarked minimum RAM requirement, guaranteed amount reclaimed, or measured FPS uplift. The app itself uses memory; closing its GUI leaves the separate restoration timer active.

## Desktop and distribution matrix

| Environment | Discovery | Actions | Validation |
| --- | --- | --- | --- |
| Arch + GNOME 51 / Wayland | Processes, systemd, GNOME extensions and known stores | Reviewed GNOME toggles + allowlisted optional user services | Primary test target |
| GNOME versions other than 51 | Discovery may work | CLI behavior unverified; panel launcher unsupported | Untested |
| KDE Plasma | Known Plasma widget/KWin script directories | No KDE plugin mutation; eligible user service backend may be usable | Not validated end to end |
| Cinnamon | Known applet/extension directories | No Cinnamon plugin mutation | Not validated end to end |
| XFCE | Known panel-plugin descriptors | No XFCE plugin mutation | Not validated end to end |
| Other window managers/desktops | Processes/systemd/known stores where accessible | No desktop-specific adapter | Untested |
| Other modern systemd distributions | Requirements must be checked individually | Experimental only | No distro support claim yet |
| X11 sessions | GTK may run | Backend/session behavior unverified | Untested |

## Discovery coverage

- Readable `/proc` process name, PID, UID and RSS. Command-line arguments are not collected.
- Loaded system and user systemd services, including loaded inactive units. Not every unit file on disk.
- Installed/live GNOME extension information, and standard GNOME store directories.
- Known KDE Plasma, KWin, Cinnamon, XFCE, XDG autostart, VS Code/Code OSS/Cursor, Chromium-family/Firefox and selected Flatpak profile locations.
- Flatpak/Snap installed app lists when their executables are present.
- System memory, cache, shared memory and swap summaries from `/proc/meminfo`.

This is a best-effort known-location scan, not a full filesystem audit. Custom profiles, inaccessible files, other users' private data, unknown plugin formats, containers, VMs and GPU allocations are not exhaustively enumerated. Installed artifacts are not necessarily active. Memory rows overlap and must not be added into predicted savings.

Discovery is wider than control: arbitrary processes, system services, browser/editor plugins and non-GNOME desktop plugins are read only.
