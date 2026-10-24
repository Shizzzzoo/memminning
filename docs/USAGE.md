# Usage guide

## Command center

The dashboard shows live available RAM, swap use, reviewable targets and the temporary-session workflow. The character card personalizes the UI. Choose Minecraft, Fortnite or VALORANT in the roster filter, or browse all eight characters. If artwork was not downloaded, generic icons appear; see [installation](INSTALLATION.md) to enable portraits.

Available RAM uses Linux's estimate of memory available to applications. A lower swap number is not automatically a better result. Memminning does not measure FPS or attribute changes in RAM entirely to its own actions.

## Inventory and selection

Open **System inventory**. The default **Reviewable targets** filter shows only currently eligible actions. Use **All inventory** or the category selector to inspect processes, system services, plugins and memory summaries. Search by name or the row's descriptive text.

Each actionable target begins at **Keep running**:

- **Disable temporarily:** an enabled GNOME extension, subject to protection rules.
- **Stop temporarily:** an allowlisted active optional user service; indexing, thumbnails or sharing may stop.
- **Soft RAM limit:** a `MemoryHigh` threshold for an eligible service cgroup. This can induce reclamation/swapping and latency; it is not a hard cap or guaranteed RAM saving.

Only one action per target can be selected. Protected and unsupported targets remain read only. Do not use the number of selected actions as a goal: changing more targets does not earn additional progress.

## Review, apply and restore

Set the duration (1–480 minutes). If using soft limits, set 64–16,384 MiB **per selected service**, not a total budget. The default is 256 MiB, but a service already subject to an equal/tighter effective limit will be rejected rather than loosened.

Select **Review gaming mode**. The dialog lists the exact actions/targets and risks. Applying requires the acknowledgment checkbox. State is revalidated again at execution time; if it changed since scanning, rescan instead of forcing the action.

A recovery journal and independent timer are established before changes. Launch your game yourself. Closing the GUI leaves the timer running. **Restore now** is available on every page when a session exists; operations serialize, so an in-progress scan/action may need to finish first.

Failed restoration is not treated as success. Follow [troubleshooting](TROUBLESHOOTING.md), preserve the journal, and retry after resolving the reported problem.

## Personalization and useful milestones

**Preferences** includes:

- Professional Mode: hides character art and progression, silences milestone audio and removes transitions.
- Milestone sounds: off by default; optional system sound when `paplay` and the sound file are available.
- Reduce motion: disables transitions while honoring the system animation setting.
- Accent themes: emerald initially; amber after a scan, teal after a valid review, violet after a completed recovery.
- Custom avatars: local PNG/JPEG under 10 MiB and 25 megapixels, stored as a bounded thumbnail. Nothing is uploaded.

All characters and system controls are available immediately. Only optional colors unlock. Milestones reward first scan, valid review, shortcut use, one restored session and five restored sessions. Repeat scans do not repeatedly earn credit; failed applies, rollbacks and incomplete recoveries are not successful sessions. History counts restored app sessions, not gaming time.

Progress remains separate from the recovery journal. Its failure must not block restoration.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+F` | Open inventory and focus search |
| `Ctrl+R` | Rescan |
| `Ctrl+Shift+R` | Restore original settings when not busy |
| `Ctrl+,` | Open preferences |

## Command line

```bash
~/.local/bin/memminning             # Open GUI
~/.local/bin/memminning --version   # Version
~/.local/bin/memminning --scan      # Read-only JSON inventory
~/.local/bin/memminning --restore   # Restore current session
```

`--recover` is used by login recovery. `--restore-session ID` is used by the restoration timer and ignores stale session IDs. There is no CLI command that silently starts gaming mode; the reviewed apply flow is in the GUI.

`--scan` may include local paths and identifiers. Review output before sharing it. The GUI's **Export diagnostics** produces a smaller local report; see [support](../SUPPORT.md).
