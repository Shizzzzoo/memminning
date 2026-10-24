# Safety model and recovery

## Action policy

Memminning runs as the desktop user. It does not request root privileges or modify system services. It never signals arbitrary PIDs, edits live browser profiles, flushes caches, changes swap or sets a hard `MemoryMax` cap.

Optional user services are positively allowlisted in `memminning/core.py`: Tracker/LocalSearch indexing, Baloo, Tumbler and Rygel variants. Their canonical identity, activity, dependencies and activation triggers are checked. Services with `RequiredBy`, `BoundBy`, `TriggeredBy` or `RefuseManualStop=yes` are excluded conservatively. Unknown services are not promoted based on memory consumption or their name alone.

GNOME extension IDs associated with this app, accessibility, keyboard input, authentication and screen locking are excluded. This is a heuristic, not proof that every other extension is safe to disable. Review each target; desktop controls or active extension features may disappear.

## Memory and process tradeoffs

Pausing a process usually leaves its memory allocated. GNOME extensions share a host, so per-extension RAM is not available; disabling one may not immediately release host memory. Linux manages reclaimable cache itself. RSS and cgroup/system memory counters can overlap.

`MemoryHigh` is a soft cgroup pressure threshold. It can cause reclaim, swap and stalls, and cannot guarantee protection from OOM. Stopped services lose in-flight work and may be reactivated through D-Bus or other dependencies. Memminning does not repeatedly stop them or mask services.

See the upstream [systemd resource-control reference](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) for the control's semantics.

## Transaction and timer behavior

1. Validate every selected action and the current service/extension state.
2. Save the original state atomically in a private recovery journal.
3. Arm and verify a user systemd restoration timer before the first mutation.
4. Record pending intent before each mutation, then record its completion.
5. On apply failure, attempt rollback immediately. Keep failed recovery entries retryable.
6. On restore, apply the recorded inverse actions and report unresolved conflicts.

The timer is independent of the GUI. Its restoration service retries failures every 30 seconds while the user manager remains available. Stale timer IDs cannot restore a newer session. Unit names begin with `memminning-restore-`.

A stopped user manager or reboot removes the transient timer. Runtime service limits disappear on reboot. Installed login recovery restores saved GNOME settings and same-boot service state. It does not start services remembered from a previous boot. If GNOME is not ready at login, recovery may require a manual retry.

## Concurrent changes and limitations

An externally changed `MemoryHigh` value is reported as a conflict rather than overwritten. Resolve it by setting the recorded original value through your system tools, then retry. Restoration writes the previous effective value as a runtime override, which can override a unit configuration edited during the session until reboot.

Outside toggles of extensions or service activity cannot always be distinguished from Memminning's actions. Restoration may override them. Avoid changing the same targets in multiple tools during a session.

Do not remove the app or delete `session.json` while a session needs recovery. GNOME settings persist; a lost journal can leave extensions disabled. No guarantee covers every third-party extension bug, desktop crash, hardware fault or filesystem failure.

## Manual recovery

```bash
~/.local/bin/memminning --restore
```

If the launcher is missing, use a compatible source checkout:

```bash
/usr/bin/python3 run.py --restore
```

Preserve the journal and inspect errors rather than deleting it to bypass an active-session check. See [troubleshooting](TROUBLESHOOTING.md) for logs and support information.

## Local data and privacy

The default state directory is `~/.local/state/memminning`, mode 0700. The journal, log, profile and diagnostic exports use mode 0600. Logs rotate at 512 KB with three backups. Profiles and custom avatars are not included in diagnostic exports.

Diagnostics contain version/environment, memory, category counts, coverage notices and the recovery journal. They omit the full inventory and replace the home path with `~`, but can still contain target identifiers, error text or other paths. Nothing is uploaded automatically. Optional character downloads happen only when explicitly invoked during setup; ordinary resource control needs no network connection.
