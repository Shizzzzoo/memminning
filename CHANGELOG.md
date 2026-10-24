# Changelog

## 1.0.0 — first public preview

- Published the first repository/release, with installation, usage, compatibility, recovery and support guides.
- Added dependency preflight and optional checksum-verified portrait downloads; publisher PNGs are not bundled in source releases.
- Added CI, contribution/security policies, issue templates and source release checksums.
- Unified version reporting while preserving the existing gaming dashboard, review policy, recovery and progression.
- Earlier 0.x entries below describe local development iterations, not separately published releases.

## 0.2.1

- Replaced generated companions with Steve, Alex, Jonesy, Peely, Jett, Sage, Phoenix and Reyna using existing character artwork.
- Added game filtering and a responsive character grid; portraits are cached locally.
- Preserved character artwork sources/checksums and archived the unused generated sheet.
- Migrated legacy selections while preserving progress and preferences.

## 0.2.0

- Gaming command center with original companion portraits and local custom-avatar import.
- Persistent mastery milestones, completed-session history and cosmetic theme rewards.
- Progress recorded after successful restoration, including independent timer recovery; failures cannot block recovery.
- Professional Mode, reduced motion, optional muted-by-default audio, peripheral feedback and keyboard shortcuts.
- Separate optional profile state; no rewards for applying more system changes and no controls gated by progression.
- Added progress failure-path tests and real GTK interaction coverage with simulated system targets.

## 0.1.0

- Native GTK 4 review UI and GNOME 51 panel launcher.
- Best-effort process/service/plugin inventory and explicit discovery notices.
- Reviewed GNOME extension toggles, allowlisted optional service stops and soft memory limits.
- Atomic state journal, separate restoration timers, manual and login recovery.
- Private rotating logs, local diagnostic exports and failure-path tests.
