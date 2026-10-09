"""
Frontend page routes (SSR HTML via Jinja2).

Per CLAUDE.md rules: routers only receive requests and return responses.
Data berasal dari service + repository (database).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.enums.event_status import EventStatus
from app.repositories import event as event_repo
from app.repositories import payment as payment_repo
from app.repositories import team as team_repo
from app.services import event_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

_STATUS_LABELS = {
    EventStatus.DRAFT: "Draft",
    EventStatus.PUBLISHED: "Published",
    EventStatus.VOTING_OPEN: "Voting Open",
    EventStatus.VOTING_CLOSED: "Voting Closed",
    EventStatus.FINISHED: "Finished",
    EventStatus.ARCHIVED: "Archived",
}


async def _get_event_by_id_or_active(session: AsyncSession, event_id: str | None = None):
    """Ambil event by id; fallback ke voting_open terbaru; fallback ke event pertama."""
    if event_id:
        ev = await event_repo.get_event(session, event_id)
        if ev and ev.deleted_at is None:
            return ev
    ev = await event_repo.get_active_event(session)
    if ev:
        return ev
    events = await event_repo.list_events(session, limit=1)
    return events[0] if events else None


def _event_dict(event) -> dict:
    return {
        "id": event.id,
        "name": event.name,
        "status": _STATUS_LABELS.get(event.status, event.status.value),
        "status_code": event.status.value,
        "is_voting_open": event.is_voting_open,
        "description": event.description or "",
        "opens_at": event.opens_at.isoformat() if event.opens_at else None,
        "closes_at": event.closes_at.isoformat() if event.closes_at else None,
        "price_per_vote": getattr(event, "price_per_vote", 10000) or 10000,
    }


def _event_with_stats_dict(event, total_teams=0, total_votes=0, total_supporters=0, progress=0) -> dict:
    d = _event_dict(event)
    d["total_teams"] = total_teams
    d["total_votes"] = total_votes
    d["total_supporters"] = total_supporters
    d["progress"] = progress
    return d


def _team_dict(team, votes: int, rank: int) -> dict:
    return {
        "id": team.id,
        "rank": rank,
        "name": team.name,
        "school": team.school or "",
        "votes": votes,
        "trend": "same",
        "logo_url": getattr(team, "logo_url", None),
        "photo_url": getattr(team, "photo_url", None),
    }


@router.get("/")
async def landing(request: Request, session: AsyncSession = Depends(get_db)):
    event = await _get_event_by_id_or_active(session)
    leaderboard = []
    if event:
        leaderboard = (await event_service.build_leaderboard(session, event.id, limit=3))["entries"]
    return templates.TemplateResponse(
        request,
        "pages/landing.html",
        {
            "event": _event_dict(event) if event else None,
            "leaderboard": leaderboard,
        },
    )


@router.get("/events")
async def events_list(
    request: Request,
    event_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    all_events_raw = await event_repo.list_events(session, limit=50)

    events_with_stats = []
    for ev in all_events_raw:
        pairs = await team_repo.get_teams_with_votes(session, ev.id)
        ev_total_votes = sum(votes for _, votes in pairs)
        payments = await payment_repo.list_successful_payments(session, event_id=ev.id, limit=5000)
        unique_donors = len(set(p.supporter_name for p in payments if p.supporter_name))
        progress = 0
        if ev.price_per_vote and ev_total_votes > 0:
            progress = min(100, int((ev_total_votes / max(1, len(pairs) * 100)) * 100)) if len(pairs) > 0 else 0
        events_with_stats.append(
            _event_with_stats_dict(
                ev,
                total_teams=len(pairs),
                total_votes=ev_total_votes,
                total_supporters=unique_donors,
                progress=progress,
            )
        )

    event = await _get_event_by_id_or_active(session, event_id)
    teams = []
    leaderboard = {"entries": []}
    donors = {"entries": []}
    if event:
        pairs = await team_repo.get_teams_with_votes(session, event.id)
        teams = [_team_dict(team, votes, rank) for rank, (team, votes) in enumerate(pairs, start=1)]
        leaderboard = await event_service.build_leaderboard(session, event.id)
        donors = await event_service.build_donors(session, event.id)

    return templates.TemplateResponse(
        request,
        "pages/events.html",
        {
            "events": events_with_stats,
            "event": _event_dict(event) if event else None,
            "all_events": events_with_stats,
            "teams": teams,
            "leaderboard": leaderboard,
            "donors": donors,
        },
    )


@router.get("/events/{event_id}/vote/{team_id}")
async def vote_page(
    request: Request,
    event_id: str,
    team_id: str,
    session: AsyncSession = Depends(get_db),
):
    event = await event_repo.get_event(session, event_id)
    if not event or event.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    team = await team_repo.get_team(session, team_id)
    if not team or team.deleted_at is not None or team.event_id != event_id:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    if not event.is_voting_open:
        return templates.TemplateResponse(
            request,
            "pages/voting_closed.html",
            {"event": _event_dict(event)},
            status_code=200,
        )

    rank_pairs = await team_repo.get_teams_with_votes(session, event_id)
    rank = next((i for i, (t, _) in enumerate(rank_pairs, start=1) if t.id == team_id), 1)
    votes = next((v for t, v in rank_pairs if t.id == team_id), 0)

    return templates.TemplateResponse(
        request,
        "pages/vote.html",
        {
            "event": _event_dict(event),
            "team": _team_dict(team, votes, rank),
        },
    )


@router.get("/leaderboard")
async def leaderboard(request: Request, session: AsyncSession = Depends(get_db)):
    event = await _get_event_by_id_or_active(session)
    entries = []
    if event:
        entries = (await event_service.build_leaderboard(session, event.id))["entries"]
    return templates.TemplateResponse(
        request,
        "pages/leaderboard.html",
        {"event": _event_dict(event) if event else None, "leaderboard": entries},
    )


@router.get("/admin/login")
async def admin_login(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(request, "pages/admin_login.html", {})


@router.get("/admin")
async def admin_dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_dashboard.html",
        {},
    )


@router.get("/admin/events")
async def admin_events(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_events.html",
        {},
    )


@router.get("/admin/transactions")
async def admin_transactions(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_transactions.html",
        {},
    )


@router.get("/admin/audit-logs")
async def admin_audit_logs(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_audit_logs.html",
        {},
    )


@router.get("/admin/leaderboard")
async def admin_leaderboard(request: Request, session: AsyncSession = Depends(get_db)):
    event = await _get_event_by_id_or_active(session)
    entries = []
    if event:
        entries = (await event_service.build_leaderboard(session, event.id))["entries"]
    return templates.TemplateResponse(
        request,
        "pages/admin_leaderboard.html",
        {"event": _event_dict(event) if event else None, "leaderboard": entries},
    )


@router.get("/admin/settings")
async def admin_settings(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_settings.html",
        {},
    )


@router.get("/admin/progress")
async def admin_progress(request: Request, session: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "pages/admin_progress.html",
        {},
    )
