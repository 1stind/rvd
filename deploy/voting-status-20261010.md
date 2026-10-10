# Scheduled voting status correction

Deployed on 10 October 2026 to https://rajavotedigital.my.id.

Public cards and event details fell back to the administrator's lifecycle label when `is_voting_open` was false. An event marked `VOTING_OPEN` therefore displayed "Voting dibuka" before its scheduled start or after its end, while checkout correctly rejected the time window.

The shared page context now labels those cases "Voting belum dimulai" or "Voting ditutup". The raw lifecycle status, eligibility rules, administrator controls, stored schedules, schema and payment logic are unchanged.

## Verification

- Regression first reproduced three failures: a future window, an expired window and an expired window without a start date.
- All 25 public rendering/status tests passed locally after the fix.
- All 79 Python tests passed against the server's isolated PostgreSQL test database. Existing deprecation/test-key warnings remain.
- Production HTTPS browser check at 390 pixels confirmed the event's open badge and participant navigation. The current schedule passed checkout's voting gate and displayed "Pembayaran belum tersedia"; no payment was submitted and no JavaScript errors occurred.
- Origin health/public/admin-login checks passed; anonymous admin API access returned 401. Service state was active with zero automatic restarts after activation.

The live schedule was read only. At verification, the event began on 9 October 2026 at 15:24 WIB and ends on 10 November 2026 at 15:24 WIB. These values had changed since the earlier diagnosis of a future start; this deployment did not edit them.

## Recovery and limits

- Active release: `/srv/rvd/releases/20261010-voting-status`, through `/srv/rvd/current`.
- Previous release: `/srv/rvd/releases/20261010-ivory-gold`.
- Fresh backup: `/var/backups/rvd/rvd-before-voting-status-20261010.dump`, mode 0600; archive listing validated, no restore drill for this backup.
- Activation used an automatic rollback trap and retained existing compiled CSS, dependencies, environment and migrations.

Real gateway processing and physical-device Safari were not tested. Gateway activation remains deferred and mock mode remains disabled. Discovery pages retain the existing five-second cache; an already-open browser page does not automatically refresh its status at a schedule boundary.
