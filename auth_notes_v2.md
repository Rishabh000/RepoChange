# Authentication Notes (v2)

Revised after the security review. Supersedes the original auth notes.

## Changes from v1
- Access token lifetime reduced from 30m to 10m.
- Added refresh-token rotation with reuse detection.
- Introduced device binding for refresh tokens on mobile clients.

## Open Questions
- Do we need step-up auth (re-prompt) for high-risk actions?
- Where do we store the token blocklist: Redis vs. database?
