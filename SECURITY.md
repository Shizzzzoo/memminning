# Security policy

## Supported release line

The latest v1 release is the current maintenance target. Earlier local 0.x development snapshots are not maintained release lines. This does not imply an audit, fixed response time or production certification.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature on the repository's **Security → Report a vulnerability** page:

https://github.com/Shizzzzoo/memminning/security/advisories/new

Include the affected version, environment, impact, reproduction steps and a minimal proof of concept. Do not include unrelated secrets or private user data. Avoid posting exploitable details in public issues while the report is being assessed. If private reporting is unavailable, open a public issue requesting a private reporting channel without describing the exploit or including sensitive files.

## Relevant boundaries

The app runs as the desktop user. It can change reviewed user-session state, so journal integrity, target policy, argument handling and restoration behavior matter. No root helper, telemetry or runtime remote updater is included. Optional artwork is explicitly fetched as data and checksum-verified. Credentials and state files must not be included in bug reports or commits.
