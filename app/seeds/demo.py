"""
Seed: demo event, teams, and system settings.
Intended for development / staging only.
"""
import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.enums.event_status import EventStatus
from app.enums.payment_gateway import PaymentGateway
from app.enums.payment_status import PaymentStatus
from app.models.event import Event
from app.models.payment import Payment
from app.models.system_settings import SystemSettings
from app.models.team import Team
from app.utils import new_id

logger = logging.getLogger(__name__)

DEMO_EVENT = {
    "name": "Kompetisi Band Antar Sekolah 2026",
    "slug": f"kompetisi-band-2026-{secrets.token_hex(3)}",
    "description": (
        "Dukung band favoritmu dan bantu mereka naik ke puncak Leaderboard. "
        "Setiap suara berasal dari pembayaran yang terverifikasi — transparan dan bisa diaudit."
    ),
    "status": EventStatus.VOTING_OPEN,
    "closes_at": datetime(2026, 8, 20, 23, 59, tzinfo=timezone.utc),
    "price_per_vote": 10000,
    "timezone": "Asia/Jakarta",
    "currency": "IDR",
}

DEMO_TEAMS = [
    ("Nada Senja", "SMA 3 Yogyakarta"),
    ("Ambyar Orchestra", "SMA 1 Sleman"),
    ("Ritme Malam", "SMK 2 Bantul"),
    ("Suara Kota", "SMA 5 Yogyakarta"),
    ("Langit Senandung", "SMA 2 Bantul"),
    ("Dawai Muda", "SMK 1 Sleman"),
]

SYSTEM_SETTINGS = [
    {"key": "maintenance_mode", "value": "false", "description": "Maintenance mode flag"},
    {"key": "leaderboard_refresh", "value": "10", "description": "Leaderboard refresh interval in seconds"},
    {"key": "queue_limit", "value": "500", "description": "Maximum queue size"},
    {"key": "cloudflare_enabled", "value": "false", "description": "Cloudflare protection enabled"},
]

DEMO_PAYMENTS = [
    {"supporter_name": "Andi Wijaya", "team_idx": 0, "amount": 1000000, "votes": 120, "qty": 10, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 5, "hours_ago": 2},
    {"supporter_name": "Andi Wijaya", "team_idx": 0, "amount": 800000, "votes": 96, "qty": 8, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 3, "hours_ago": 4},
    {"supporter_name": "Andi Wijaya", "team_idx": 0, "amount": 700000, "votes": 70, "qty": 7, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 1, "hours_ago": 1},
    {"supporter_name": "Budi Santoso", "team_idx": 1, "amount": 1000000, "votes": 120, "qty": 10, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 4, "hours_ago": 3},
    {"supporter_name": "Budi Santoso", "team_idx": 1, "amount": 800000, "votes": 80, "qty": 8, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 2, "hours_ago": 5},
    {"supporter_name": "Citra Dewi", "team_idx": 2, "amount": 3200000, "votes": 320, "qty": 32, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 6, "hours_ago": 1},
    {"supporter_name": "Dina Rahayu", "team_idx": 3, "amount": 750000, "votes": 75, "qty": 15, "pkg_code": "silver", "pkg_label": "Silver", "days_ago": 2, "hours_ago": 2},
    {"supporter_name": "Eka Putri", "team_idx": 4, "amount": 700000, "votes": 70, "qty": 7, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 3, "hours_ago": 6},
    {"supporter_name": "Eka Putri", "team_idx": 4, "amount": 500000, "votes": 50, "qty": 5, "pkg_code": "gold", "pkg_label": "Gold", "days_ago": 1, "hours_ago": 3},
    {"supporter_name": "Fajar Nugroho", "team_idx": 5, "amount": 500000, "votes": 50, "qty": 10, "pkg_code": "silver", "pkg_label": "Silver", "days_ago": 1, "hours_ago": 4},
    {"supporter_name": "Gita Olivia", "team_idx": 0, "amount": 900000, "votes": 90, "qty": 18, "pkg_code": "silver", "pkg_label": "Silver", "days_ago": 2, "hours_ago": 1},
]


async def seed_demo() -> None:
    async with async_session() as session:
        event_id = new_id("evt")
        event = Event(
            id=event_id,
            name=DEMO_EVENT["name"],
            slug=DEMO_EVENT["slug"],
            description=DEMO_EVENT["description"],
            status=DEMO_EVENT["status"],
            closes_at=DEMO_EVENT["closes_at"],
            price_per_vote=DEMO_EVENT["price_per_vote"],
            timezone=DEMO_EVENT["timezone"],
            currency=DEMO_EVENT["currency"],
        )
        session.add(event)

        teams = []
        for i, (name, school) in enumerate(DEMO_TEAMS):
            team = Team(
                id=new_id("tm"),
                event_id=event_id,
                name=name,
                school=school,
                sort_order=i,
            )
            teams.append(team)
            session.add(team)

        for setting in SYSTEM_SETTINGS:
            existing = await session.get(SystemSettings, setting["key"])
            if not existing:
                session.add(
                    SystemSettings(
                        key=setting["key"],
                        value=setting["value"],
                        description=setting["description"],
                    )
                )

        await session.commit()

        for payment_data in DEMO_PAYMENTS:
            paid_at = datetime.now(timezone.utc).replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            paid_at = paid_at.replace(day=paid_at.day - payment_data["days_ago"])
            session.add(
                Payment(
                    team_id=teams[payment_data["team_idx"]].id,
                    event_id=event_id,
                    supporter_name=payment_data["supporter_name"],
                    supporter_email=f"{payment_data['supporter_name'].lower().replace(' ', '.')}@example.com",
                    supporter_phone="081234567890",
                    is_anonymous=False,
                    package_code=payment_data["pkg_code"],
                    package_label=payment_data["pkg_label"],
                    qty=payment_data["qty"],
                    amount=payment_data["amount"],
                    votes=payment_data["votes"],
                    vote_snapshot={
                        "unit_price": 10000,
                        "base_votes": payment_data["votes"],
                        "bonus_votes": 0,
                    },
                    status=PaymentStatus.SUCCESS,
                    payment_gateway=PaymentGateway.MIDTRANS,
                    payment_channel=None,
                    currency="IDR",
                    signature_key="dummy-signature",
                    midtrans_order_id=f"ORDER-{new_id('ord')}",
                    midtrans_transaction_id=f"TRX-{new_id('trx')}",
                    paid_at=paid_at,
                    settled_at=paid_at,
                )
            )

        await session.commit()
        logger.info("Demo seed selesai: event=%s, tim=%d", event_id, len(DEMO_TEAMS))
