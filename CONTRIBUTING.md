# Contributing

Issues, documentation corrections and tested compatibility reports are welcome. For behavior changes, describe the user-visible problem and resulting behavior, then include relevant validation.

Read [development](docs/DEVELOPMENT.md) and [safety](docs/SAFETY.md) before changing action logic.

## Ground rules

- Keep discovery separate from permission to modify a target.
- Do not add root operations, arbitrary process killing or automatic target selection as incidental changes.
- Every new action needs explicit policy, reversible state, a review description and failure/recovery tests.
- Progression and cosmetics must never gate safety controls or block restoration.
- Preserve the separation between optional profile data and the recovery journal.
- Test new desktop adapters in disposable sessions; do not claim support from directory detection alone.
- Do not commit user logs, recovery journals, credentials, private paths or downloaded third-party character PNGs.
- Only submit work you have the right to contribute. Memminning code contributions are under the project's MIT license; third-party art is separate.

## Pull request checklist

1. Explain the concrete trigger and resulting behavior.
2. Keep the patch scoped and follow existing Python style.
3. Run `python3 -m unittest discover -s tests -v`.
4. For GUI changes, run the interaction test and inspect the rendered app.
5. For core actions, add failure-path coverage and document remaining live-test limits.
6. Update guides and the changelog when user behavior changes.

Do not report a security vulnerability publicly. Follow [SECURITY.md](SECURITY.md).
