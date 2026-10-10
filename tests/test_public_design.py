"""Public rendering and event-specific leaderboard regression checks."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request

from app.enums.event_status import EventStatus
from app.routers import pages


def request(path='/'):
    return Request({'type': 'http', 'method': 'GET', 'path': path,
                    'headers': [], 'query_string': b'', 'scheme': 'http',
                    'server': ('test', 80)})


@pytest.mark.parametrize('name', ['landing', 'events', 'leaderboard', 'vote', 'voting_closed'])
def test_public_templates_render(name):
    event = {'id': 'event-example', 'name': 'Creative Awards', 'description': '',
             'is_voting_open': True, 'status': 'Voting Open', 'banner_url': None,
             'closes_at': None}
    team = {'id': 'participant-example', 'name': 'Example Participant', 'votes': 12}
    html = pages.templates.get_template(f'pages/{name}.html').render(
        request=request(), event=event, all_events=[event], leaderboard=[], team=team)
    assert '/static/css/public.css' in html
    assert 'public-site' in html
    assert '/static/images/raja-voting-logo.png' in html
    assert 'via Midtrans' not in html
    assert 'id="main-content"' in html


@pytest.mark.parametrize('name', ['landing', 'events', 'leaderboard'])
def test_public_empty_states_render(name):
    html = pages.templates.get_template(f'pages/{name}.html').render(
        request=request(), event=None, all_events=[], leaderboard=[])
    assert 'public-site' in html
    assert '/static/images/raja-voting-logo.png' in html
    assert 'via Midtrans' not in html
    assert 'href="/events"' in html


@pytest.mark.parametrize('name,path', [
    ('dashboard', '/admin'), ('events', '/admin/events'),
    ('transactions', '/admin/transactions'), ('audit_logs', '/admin/audit-logs'),
    ('settings', '/admin/settings'), ('leaderboard', '/admin/leaderboard'),
    ('progress', '/admin/progress'),
])
def test_admin_uses_the_shared_theme(name, path):
    html = pages.templates.get_template(f'pages/admin_{name}.html').render(
        request=request(path), event=None, leaderboard=[])
    assert '/static/css/public.css' in html
    assert '/static/css/admin.css' in html
    assert 'admin-sidebar' in html
    assert 'public-header' not in html
    assert html.count('id="sidebar"') == 1
    assert html.count('aria-current="page"') == 1
    assert 'id="admin-main"' in html


def test_admin_login_has_labeled_credentials_and_error_feedback():
    html = pages.templates.get_template('pages/admin_login.html').render(
        request=request('/admin/login'))
    assert '/static/css/admin.css' in html
    assert 'autocomplete="username"' in html
    assert 'autocomplete="current-password"' in html
    assert 'for="email"' in html
    assert 'for="password"' in html
    assert 'role="alert"' in html
