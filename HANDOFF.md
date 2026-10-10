# Raja Voting Digital handoff

## Current release

The approved ivory/navy/gold UI and the existing hardened backend are combined in this repository. They are running at https://rajavotedigital.my.id from `/srv/rvd/releases/20261010-ivory-gold`, selected through `/srv/rvd/current`.

The visual release did not change the previously deployed Python backend, schema, dependency lock or checkout client. Compared with the older GitHub `main`, this branch also records those earlier production improvements: payment/vote integrity, concurrency controls, SSE resource handling, shared caching, middleware hardening and the associated regression tests.

## Architecture and contracts

- Routers handle HTTP and template context; services contain business logic; repositories perform database access.
- PostgreSQL migrations are the schema authority. Migration head is `b7c8d9e0f1a2`; it adds `teams.previous_rank`, a unique vote-log payment index and payment lookup indexes. Before applying it elsewhere, resolve any historical duplicate vote-log payment IDs.
- Admin authentication uses `/api/v1/auth/admin/login` and a signed JWT bearer token. Provision production accounts separately; no account or database snapshot belongs in Git.
- Successful payments grant the purchased quantity once, with an immutable snapshot. Event/payment locks and atomic updates preserve concurrent totals and ranks.
- SSE uses Redis to coordinate workers, releases request database sessions before streaming and coalesces updates. Discovery HTML is cached for five seconds per worker.
- `public_base.html`, `admin_base.html` and scoped CSS provide the visual system. Native checkout dialogs, authenticated exports and escaped admin table rendering are retained.

## Operations

Use the existing systemd/Caddy deployment configuration and hash-locked Python dependencies. Build Tailwind before starting a release. Runtime environment and database state live outside release directories. See [deployment notes](deploy/README.md) and [visual release evidence](deploy/ivory-gold-20261010.md).

The previous release and a fresh PostgreSQL backup remain available. No database or credential changes accompanied the visual rollout. Source was initially deployed directly; the integration branch records that running state for review.

## Remaining limits

Production gateway activation is deferred. Mock mode is disabled, and unavailable checkout must remain closed until the Snap/QRIS response contract is completed and tested. Queue enforcement and CAPTCHA remain unfinished. Some settings are stored administrative notes rather than implemented runtime controls; the UI says so. Project progress does not invent completion percentages.

Scheduled/off-site backups and the previously observed large independent-connection burst failures remain operational follow-ups. This PR does not claim to resolve them. Local SQLite previews are visual fixtures, not evidence of PostgreSQL concurrency or real gateway behavior.
