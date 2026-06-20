# Authentication Notes

We evaluated several authentication strategies for the platform.

## Decision
We selected **OAuth2** with PKCE for the public client, backed by short-lived
JWT access tokens and rotating refresh tokens. Sessions are revocable through a
server-side token blocklist.

## Rationale
- OAuth2 is an industry standard and integrates with existing identity providers.
- PKCE protects the authorization code exchange on mobile and SPA clients.
- Short-lived access tokens limit the blast radius of a leaked token.
