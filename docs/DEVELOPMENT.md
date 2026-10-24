# Development and releases

## Structure

| Path | Responsibility |
| --- | --- |
| `run.py` | GUI/CLI entrypoint and top-level error logging |
| `memminning/core.py` | Discovery, positive action policy, durable transactions and recovery |
| `memminning/gui.py` | Inventory, reviewed action flow and worker orchestration |
| `memminning/gameui.py` | Native dashboard, preferences, avatars and feedback |
| `memminning/progress.py` | Optional local milestones/history, independent of recovery |
| `memminning/artwork.py` | Explicit bounded/checksummed optional image downloads |
| `gnome-extension/` | GNOME 51 panel launcher |
| `install.py` | Per-user dependency check, installation and updates |
| `scripts/` | Source-checkout helpers |
| `tests/` | Core/progress/download tests and native GUI checks |
| `.github/workflows/tests.yml` | Python and isolated GTK CI |

The project uses system Python/GTK rather than pip packaging. Original code is MIT-licensed; optional character art is separate.

## Local checks

Core tests require Python 3.10+ and no GTK imports, network or desktop mutation:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q memminning run.py install.py tests scripts
```

Graphical tests use distribution Python and a graphical session:

```bash
/usr/bin/python3 tests/gui_interactions.py
/usr/bin/python3 tests/gui_smoke.py
```

The interaction test uses fake system operations and temporary state. The smoke test scans real readable system state but does not apply gaming actions. It can record a legitimate first-scan milestone in the current user's local profile. GUI visual capture uses an isolated profile and writes local screenshots, which are ignored unless explicitly selected for publication.

The real-timer test creates an isolated empty recovery journal and a harmless transient user timer:

```bash
/usr/bin/python3 tests/integration_timer.py
```

It does not stop any desktop service or toggle an extension. Running it requires a working user systemd manager. Live stop/limit/extension failure scenarios still need disposable desktop testing.

## Adding an integration

Add discovery and clearly label its limitations before implementing actions. An action adapter must define target identity, explicit eligibility, known risks, preconditions, original-state capture, apply verification, rollback and retry behavior. Add stale-state, partial-failure, crash-intent and concurrent-change tests. Do not make an unknown target actionable just because it consumes memory.

The profile schema and recovery schema are independent. Unknown schemas fail closed. Cosmetic writes must never cause restoration to fail.

## CI

Core tests run on Python 3.10 and 3.14. The GTK job uses Ubuntu's system Python with GTK/PyGObject, D-Bus and Xvfb to exercise the GUI against simulated targets. CI does not require copyrighted portrait downloads, GitHub secrets, or root-level service control. It is code/UI validation, not certification of live Ubuntu desktop support.

## Release process

1. Restore local active sessions; ensure the release does not accidentally include state or logs.
2. Update `memminning/__init__.py`, documentation and changelog. The CLI and diagnostics use that version.
3. Run unit, relevant GUI and timer checks. Validate a clean checkout without optional art.
4. Confirm README links, support boundaries, third-party notices and optional-asset hashes.
5. Commit and tag the exact release, then push both commit and tag.
6. Build the source archive from Git, so ignored local artwork/state cannot leak into it.
7. Publish the archive and SHA-256 list with release notes. Mark a public preview as a prerelease until broader validation supports a stable designation.

Example archive commands from a release checkout:

```bash
mkdir -p dist
git archive --format=tar.gz --prefix=memminning-1.0.0/ v1.0.0 > dist/memminning-v1.0.0.tar.gz
cd dist
sha256sum memminning-v1.0.0.tar.gz > SHA256SUMS
```

Release archives are source releases, not self-contained binaries. Users still need the listed system dependencies. There are no signed releases, AUR packages or automatic updates yet.
