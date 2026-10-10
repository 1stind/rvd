"""An open SSE stream must not hold a database connection for its whole lifetime."""
import asyncio
from contextlib import suppress

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_open_stream_does_not_pin_a_db_connection(async_client, db_session, test_data):
    stream = asyncio.create_task(
        async_client.get(f"/api/v1/leaderboard/stream?event_id={test_data['event'].id}")
    )
    await asyncio.sleep(1)  # initial ranking has been sent; the stream is now idle

    pinned = (
        await db_session.execute(
            text(
                "select count(*) from pg_stat_activity "
                "where datname = current_database() and pid <> pg_backend_pid() "
                "and state like 'idle in transaction%'"
            )
        )
    ).scalar_one()

    stream.cancel()
    with suppress(asyncio.CancelledError):
        await stream
    assert pinned == 0
