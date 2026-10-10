# Tencent deployment

Production runs at https://rajavotedigital.my.id. The current release combines the approved ivory/navy/gold design with the backend already deployed on Tencent. See [release verification and recovery](ivory-gold-20261010.md).

## Existing runtime

| Component | Configuration |
| --- | --- |
| Release | `/srv/rvd/current` → `/srv/rvd/releases/20261010-ivory-gold` |
| Service | `rvd.service`, dedicated `rvd` user, two uvicorn workers on loopback port 8000 |
| Python | 3.12, `/srv/rvd/venv`, dependencies from hash-verified `requirements.lock` |
| Database | PostgreSQL 16, loopback only, separate production and disposable test databases |
| Redis | Shared cache, rate limits and SSE backplane; separate test database |
| Environment | `/etc/rvd/production.env`, outside source control |
| Proxy | Caddy with HTTPS and unbuffered SSE; Cloudflare Full (strict) |
| Assets | Prebuilt Tailwind and five-minute static cache; versioned URLs after a rebuild/restart |

The checked-in [systemd unit](rvd.service) and [Caddy configuration](Caddyfile) describe the existing runtime. Database data, runtime configuration and credentials stay outside release directories. New installations must provision them separately; copying source does not create an admin account or populate the database.

For a release, validate the source and locked dependencies, build CSS, test against the isolated database, create a protected database backup, apply any required migrations, then switch the active release symlink and restart the service. Keep the previous release for rollback and verify health, public pages and protected admin access after switching. The visual release required no new migration because production was already at `b7c8d9e0f1a2`.

## Verification and limits

The current release passed 70 Python checks on the isolated server database and production browser checks across desktop and mobile widths. The integrated workspace also passes 18 JavaScript tests. Details and file-hash evidence are in [the release report](../docs/tencent-ivory-gold-verification.json).

Production mock payments remain disabled and real gateway integration is deferred. A checkout must remain unavailable until the Snap/QRIS contract has been completed and verified. Never run demo seeding or settlement/load tests against production.

The previous same-host restore drill succeeded. The fresh visual-release backup has a validated archive listing but was not independently restored. Scheduled/off-site backups are still outstanding. Earlier high-volume independent-connection tests exposed unresolved transport limits; this visual release does not claim a new throughput SLA or repeat sustained/distributed load testing.
