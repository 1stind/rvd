"""Concurrent website browsing, SSE viewers and mock-only voting.

    python scripts/loadtest.py --base http://127.0.0.1:8010 --event evt_x \
        --viewers 1000 --voters 100 --burst --settle --json report.json

Use an isolated staging database. Payment traffic is refused unless the mock
simulator is verified before any invoices are created. This is HTTP load, not
browser rendering or a real payment-gateway test.
"""
import argparse
import asyncio
import json
import math
import random
import time
import uuid
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import httpx

try:
    import resource
except ImportError:  # Windows does not expose POSIX descriptor limits.
    resource = None

latencies: dict[str, list[float]] = defaultdict(list)
errors: dict[str, int] = defaultdict(int)
invoice_starts: list[float] = []


def file_descriptor_budget(connections):
    if resource is None:
        return {"checked": False}
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    required = connections + 64  # Leave room for the event loop, logs and resolver.
    return {"checked": True, "soft": soft, "hard": hard, "required": required,
            "sufficient": soft == resource.RLIM_INFINITY or soft >= required}


def pct(values, p):
    """Nearest-rank percentile; never extrapolates beyond observed latency."""
    return sorted(values)[max(0, math.ceil(len(values) * p / 100) - 1)] if values else 0


def integrity(votes_before, votes_after, granted, streams):
    expected = votes_before + granted
    return {
        "votes_before": votes_before, "votes_after": votes_after,
        "votes_granted": granted, "expected_total": expected,
        "leaderboard_matches": votes_after == expected,
        "sse_viewers_at_expected_total": sum(s["last_votes"] == expected for s in streams),
        "all_sse_match": all(s["last_votes"] == expected for s in streams),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--event", required=True)
    parser.add_argument("--users", type=int, help="legacy: set both viewers and voters")
    parser.add_argument("--viewers", type=int, default=None, help="SSE connections plus browsing sessions (default 1000)")
    parser.add_argument("--voters", type=int, default=None, help="mock voting sessions (default 100)")
    parser.add_argument("--burst", action="store_true", help="release browsing together and synchronize invoice creation")
    parser.add_argument("--settle", action="store_true", help="required for voters; permits isolated mock staging invoices and settlement")
    parser.add_argument("--ready-timeout", type=float, default=60)
    parser.add_argument("--push-timeout", type=float, default=15)
    parser.add_argument("--json", type=Path, help="write machine-readable results")
    args = parser.parse_args(argv)
    args.viewers = args.viewers if args.viewers is not None else (args.users if args.users is not None else 1000)
    args.voters = args.voters if args.voters is not None else (args.users if args.users is not None else 100)
    if min(args.viewers, args.voters) < 0 or args.viewers + args.voters == 0:
        parser.error("viewers and voters must be nonnegative with at least one session")
    if args.ready_timeout <= 0 or args.push_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.voters and not args.settle:
        parser.error("voters require --settle and a verified mock staging server; use --voters 0 for read-only load")
    args.base = args.base.rstrip("/")
    host = urlparse(args.base).hostname
    if not host or urlparse(args.base).scheme not in ("http", "https"):
        parser.error("base must be an HTTP(S) URL")
    if args.voters and host not in ("localhost", "127.0.0.1", "::1"):
        parser.error("mock invoices require loopback; run on the isolated staging host or use an SSH tunnel")
    return args


async def timed(client, name, method, url, **kw):
    start = time.perf_counter()
    try:
        response = await client.request(method, url, **kw)
        if not 200 <= response.status_code < 300:
            errors[f"{name} HTTP {response.status_code}"] += 1
            return None
        return response
    except httpx.HTTPError as exc:
        errors[f"{name} {type(exc).__name__}"] += 1
        return None
    finally:
        latencies[name].append((time.perf_counter() - start) * 1000)


def api_data(response, name):
    if response is None:
        return None
    try:
        body = response.json()
        if body.get("success") is not True or "data" not in body:
            raise ValueError("invalid API envelope")
        return body["data"]
    except (ValueError, AttributeError):
        errors[f"{name} invalid JSON/envelope"] += 1
        return None


async def browse(client, base, event_id, start, burst):
    await start.wait()
    if not burst:
        await asyncio.sleep(random.uniform(0, 10))
    for label, url in (("GET /", "/"), ("GET /events", "/events"),
                       ("GET event detail", f"/events?event_id={event_id}")):
        await timed(client, label, "GET", base + url)


async def viewer(client, base, event_id, state, stop):
    started = time.perf_counter()
    try:
        async with client.stream("GET", f"{base}/api/v1/leaderboard/stream", params={"event_id": event_id},
                                 timeout=httpx.Timeout(30, read=None)) as response:
            if response.status_code != 200 or "text/event-stream" not in response.headers.get("content-type", ""):
                errors[f"SSE invalid response {response.status_code}"] += 1
                return
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    body = json.loads(line[5:].strip())
                    if body.get("type") != "leaderboard":
                        continue
                    if body.get("event_id") != event_id:
                        raise ValueError("wrong event stream")
                    state["last_votes"] = sum(e["votes"] for e in body["data"]["entries"])
                    state["messages"] += 1
                    if not state["ready"].is_set():
                        latencies["SSE ready"].append((time.perf_counter() - started) * 1000)
                        state["ready"].set()
            if not stop.is_set():
                errors["SSE ended early"] += 1
    except asyncio.CancelledError:
        if not stop.is_set():
            errors["SSE cancelled early"] += 1
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        if not stop.is_set():
            errors[f"SSE {type(exc).__name__}"] += 1


async def voter(client, args, team_ids, n, run_id, start, invoice_barrier):
    await start.wait()
    if not args.burst:
        await asyncio.sleep(random.uniform(0, 10))
    team_id = team_ids[n % len(team_ids)]
    page = await timed(client, "GET vote page", "GET", f"{args.base}/events/{args.event}/vote/{team_id}")
    if invoice_barrier:
        await asyncio.wait_for(invoice_barrier.wait(), timeout=args.ready_timeout)
    if page is None:
        return 0
    qty = n % 5 + 1
    invoice_starts.append(time.perf_counter())
    created = api_data(await timed(client, "POST /payments", "POST", f"{args.base}/api/v1/payments", json={
        "event_id": args.event, "team_id": team_id, "qty": qty,
        "supporter_name": f"Load test {n}", "supporter_phone": f"0899{run_id}{n:05d}",
        "idempotency_key": f"load-{run_id}-{n}",
    }), "POST /payments")
    if not isinstance(created, dict) or not created.get("id") or created.get("is_mock") is not True:
        errors["invoice missing or not mock"] += 1
        return 0
    payment_id = created["id"]
    for _ in range(2):
        await asyncio.sleep(5)
        api_data(await timed(client, "GET payment status", "GET", f"{args.base}/api/v1/payments/{payment_id}/status"), "GET payment status")
    done = api_data(await timed(client, "POST simulate", "POST", f"{args.base}/api/v1/payments/mock/{payment_id}/simulate",
                                json={"action": "success"}), "POST simulate")
    if not isinstance(done, dict) or done.get("status") != "SUCCESS" or done.get("votes") != qty:
        errors["settlement result mismatch"] += 1
        return 0
    return qty


async def run(args):
    latencies.clear()
    errors.clear()
    invoice_starts.clear()
    started = time.perf_counter()
    report = {"base": args.base, "event": args.event, "viewers": args.viewers, "voters": args.voters,
              "burst": args.burst, "mock_only": bool(args.voters), "passed": False}
    streams = [{"ready": asyncio.Event(), "last_votes": None, "messages": 0} for _ in range(args.viewers)]
    stop = asyncio.Event()
    stream_tasks = []
    connections = max(10, args.viewers * 2 + args.voters + 10)
    limits = httpx.Limits(max_connections=connections,
                         max_keepalive_connections=max(10, args.viewers + args.voters))
    async with httpx.AsyncClient(limits=limits, timeout=30) as client:
        try:
            report["file_descriptors"] = file_descriptor_budget(connections)
            budget = report["file_descriptors"]
            if budget.get("sufficient") is False:
                raise ValueError(
                    f"Load generator RLIMIT_NOFILE soft={budget['soft']} is below required={budget['required']} "
                    f"(hard={budget['hard']}). Raise this shell's limit with ulimit -n {budget['required']} "
                    "within the hard limit, or reduce viewers/voters. No HTTP requests or invoices were created."
                )
            if args.voters:
                # An unguessable nonexistent invoice makes the probe non-mutating.
                probe = await client.post(f"{args.base}/api/v1/payments/mock/load-probe-{uuid.uuid4().hex}/simulate",
                                          json={"action": "pending"})
                if probe.status_code != 400 or probe.json().get("message") != "Invoice tidak ditemukan":
                    raise ValueError("mock simulator not verified; no invoices created")
                report["mock_verified"] = True
            initial = api_data(await timed(client, "GET leaderboard initial", "GET", f"{args.base}/api/v1/leaderboard",
                                           params={"event_id": args.event}), "initial leaderboard")
            if not initial or not isinstance(initial.get("entries"), list):
                raise ValueError("initial leaderboard unavailable")
            team_ids = [entry["team_id"] for entry in initial["entries"]]
            votes_before = sum(entry["votes"] for entry in initial["entries"])
            if args.voters and not team_ids:
                raise ValueError("voting event has no participants")
            stream_tasks = [asyncio.create_task(viewer(client, args.base, args.event, state, stop)) for state in streams]
            await asyncio.wait_for(asyncio.gather(*(s["ready"].wait() for s in streams)), timeout=args.ready_timeout)
            report["sse_ready_before_traffic"] = sum(s["ready"].is_set() for s in streams)
            start = asyncio.Event()
            barrier = asyncio.Barrier(args.voters) if args.burst and args.voters else None
            run_id = str(time.time_ns())[-10:]
            readers = [asyncio.create_task(browse(client, args.base, args.event, start, args.burst)) for _ in streams]
            voters = [asyncio.create_task(voter(client, args, team_ids, n, run_id, start, barrier)) for n in range(args.voters)]
            traffic_start = time.perf_counter()
            start.set()
            results = await asyncio.gather(*readers, *voters, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    errors[f"session {type(result).__name__}"] += 1
            granted = sum(value for value in results[len(readers):] if isinstance(value, int))
            report["traffic_seconds"] = round(time.perf_counter() - traffic_start, 3)
            deadline = time.perf_counter() + args.push_timeout
            votes_after = None
            while True:
                final = api_data(await timed(client, "GET leaderboard final", "GET", f"{args.base}/api/v1/leaderboard",
                                             params={"event_id": args.event}), "final leaderboard")
                votes_after = sum(e["votes"] for e in final["entries"]) if final else None
                if votes_after == votes_before + granted and all(s["last_votes"] == votes_after for s in streams):
                    break
                if time.perf_counter() >= deadline:
                    break
                await asyncio.sleep(.2)
            report["integrity"] = integrity(votes_before, votes_after, granted, streams)
            if not report["integrity"]["leaderboard_matches"] or not report["integrity"]["all_sse_match"]:
                errors["vote integrity mismatch"] += 1
            report["invoice_start_spread_ms"] = round((max(invoice_starts) - min(invoice_starts)) * 1000, 3) if invoice_starts else None
            report["invoices_attempted"] = len(invoice_starts)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, TimeoutError) as exc:
            errors[f"setup/run {type(exc).__name__}"] += 1
            report["failure"] = str(exc) or "SSE readiness timed out"
        finally:
            stop.set()
            for task in stream_tasks:
                task.cancel()
            await asyncio.gather(*stream_tasks, return_exceptions=True)
    report["sse"] = {"requested": args.viewers, "ready": sum(s["ready"].is_set() for s in streams),
                     "messages": sum(s["messages"] for s in streams)}
    report["latency_ms"] = {name: {"n": len(values), "p50": round(pct(values, 50), 2),
                                   "p95": round(pct(values, 95), 2), "p99": round(pct(values, 99), 2),
                                   "max": round(max(values), 2)} for name, values in latencies.items()}
    report["errors"] = dict(errors)
    report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    report["passed"] = not errors and "integrity" in report
    return report


async def main():
    args = parse_args()
    report = await run(args)
    rendered = json.dumps(report, indent=2)
    if args.json:
        args.json.write_text(rendered + "\n")
    print(rendered)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
