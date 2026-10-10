# Ivory, navy and gold production release

Deployed on 10 October 2026 to https://rajavotedigital.my.id with owner authorization.

The public site and organizer workspace share the approved design. The supplied RV logo is used for site branding and browser icons; the QRIS/Midtrans footer badge is removed. Search, participant filters, the top-three podium, keyboard navigation, and payment-unavailable state are retained. The checkout client, backend Python, database migrations and dependency lock are byte-for-byte unchanged from the previous running release. Production uses compiled Tailwind and versioned asset URLs.

## Deployment and recovery

- Active symlink: `/srv/rvd/current` → `/srv/rvd/releases/20261010-ivory-gold`.
- Previous release retained: `/srv/rvd/releases/20261010-general-events`.
- Fresh PostgreSQL custom-format backup: `/var/backups/rvd/rvd-before-ivory-gold-20261010.dump` (postgres-owned, mode 0600); archive listing validated. This new backup was not restore-tested; the earlier initial backup had a successful restore drill.
- Existing systemd service, environment files, database, credentials, reverse proxy and firewall were preserved. No database migration was needed. Production mock payments remain disabled and gateway activation remains deferred.
- Activation had a rollback trap and checked health, expected new branding, absence of the removed badge, compiled CSS and anonymous admin API rejection.

## Verification

70 Python tests passed against the server's isolated test database; 16 JavaScript tests passed before deployment. The initial merge failed the published-event discovery test; the searchable homepage catalog was restored before the passing run. Browser checks cover public pages, disabled checkout, search, participant navigation, real login, invalid credentials, filters, dialog opening, logout and responsive layouts.

Through the production HTTPS domain, the supplied logo hash matched, public pages returned 200, anonymous admin API access returned 401, existing admin login succeeded, and all seven admin pages fit widths of 320, 390 and 1440 pixels without JavaScript errors. Long audit records initially overflowed at 320 pixels; wrapping and detail styles were corrected and the complete production browser check passed. No event, settings or payment data was written by the production smoke test. User/event/payment counts remained 1/0/0.

126 deployed app/migration file hashes match both the canonical source at `/Users/anb-0826007/orca/rvd` and the design workspace. Evidence: [verification report](../docs/tencent-ivory-gold-verification.json). The initial production rollout was performed before the integration branch was committed.

Real payment processing, sustained/distributed load, physical devices and every CRUD/export operation were not retested for this visual release. Temporary local fixtures and preview credentials were not deployed.
