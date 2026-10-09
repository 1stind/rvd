"""
Seeder — backward compatibility wrapper.

New seeding is done via CLI:
    python -m app.seeds run demo
    python -m app.seeds run admin --email admin@domain.com --password rahasia
    python -m app.seeds run all

This module is kept for backward compatibility and delegates to app.seeds.
"""
import logging

logger = logging.getLogger(__name__)


async def seed_if_empty() -> None:
    """Legacy: seed demo + admin if database is empty."""
    from app.seeds.admin import seed_admin
    from app.seeds.demo import seed_demo

    logger.warning("seed_if_empty() is deprecated. Use: python -m app.seeds run all")
    await seed_demo()
    await seed_admin()
