# Troubleshooting

If gaming-mode restoration is incomplete, preserve `session.json` and try **Restore now** or `~/.local/bin/memminning --restore`. Do not delete the journal to make the error disappear.

| Symptom | What to check |
| --- | --- |
| `No module named gi` or missing Gtk/Adw namespace | Use `/usr/bin/python3`; install the distribution's PyGObject, GTK 4 and libadwaita packages. Conda/venv Python may not see system bindings. Run `install.py --check`. |
| Display or session-bus errors | Launch from a terminal inside your logged-in desktop. SSH, root shells, containers and sandboxes may not have your user session access. |
| `Failed to connect to user scope bus` | Check `systemctl --user status` in your desktop session. Do not run the app with sudo to work around a user-bus problem. |
| No reviewable targets | Check scan notices and All inventory. Unknown/protected targets, inactive services, dependency restrictions or missing GNOME integration can legitimately leave nothing actionable. |
| GNOME panel launcher does not appear | Use GNOME 51, log out/in, then enable Memminning in Extensions. The main app can run without the panel launcher. |
| Character portraits show generic icons | Install with `--with-character-art`, or import a local avatar. Portrait binaries are optional and excluded from release archives. |
| Artwork checksum mismatch | Stop using that download; keep the original. Report the character and error. A source may have changed. Do not remove checksum validation. |
| Timer cannot be armed | Check `systemd-run --version`, `systemctl --user status`, and user-unit logs. No gaming actions should apply if arming fails. |
| `MemoryHigh` unavailable or rejected | A usable cgroup v2 memory controller/user delegation is required. A selected value also cannot loosen an existing tighter limit. |
| Stopped service comes back | D-Bus or another component may reactivate it. The app does not mask or repeatedly kill it. Restore/review the session normally. |
| MemoryHigh changed outside Memminning | Inspect the saved original value and current service state. Resolve the conflict before retrying; don't blindly overwrite other tools' settings. |
| Recovery-needed / extension cannot re-enable | Ensure GNOME/session services are available and the extension is installed. Retry restoration; inspect its own errors if it cannot load. |
| Profile cannot be read | Progress is optional and separate from recovery. Preserve `profile.json` for diagnosis. Never delete `session.json` when addressing a cosmetic/profile problem. |
| Unknown GTK theme/settings warnings | Check whether the app itself fails. System-wide GTK configuration can emit warnings; include relevant errors in a report, not an entire private environment dump. |

## Collect useful diagnostics

Use **Export diagnostics** in the GUI. It saves a JSON report locally and displays the file path. Detailed logs are beside it in `$XDG_STATE_HOME/memminning`, default `~/.local/state/memminning/`.

Helpful read-only commands:

```bash
~/.local/bin/memminning --version
/usr/bin/python3 --version
gnome-shell --version
systemctl --version
systemctl --user list-timers 'memminning-restore-*'
journalctl --user -u 'memminning-restore-*' --since '1 hour ago'
```

`gnome-shell` may not exist outside GNOME. The absence of a timer after a completed session is normal. Full `--scan` output can contain more personal detail than the diagnostic export.

Review every attachment before posting. Remove private identifiers, unrelated paths and secrets. Never post credentials, browser data or an unredacted environment dump.

## Report or request support

Use [GitHub Issues](https://github.com/Shizzzzoo/memminning/issues). Include the version, distribution, kernel, desktop/session, reproduction steps, chosen actions and whether restoration succeeded. Use the bug template. Compatibility results from other distributions/devices are welcome, but do not imply support until validated.

Security-sensitive reports should follow [SECURITY.md](../SECURITY.md) rather than a public issue.
