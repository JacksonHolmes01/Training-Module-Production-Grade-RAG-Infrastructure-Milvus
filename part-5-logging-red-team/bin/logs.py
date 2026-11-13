#!/usr/bin/env python3
"""
logs.py: search this lab's security-relevant logs.

Usage (from the part-5 folder):
  python3 bin/logs.py                         last 15 minutes, every event
  python3 bin/logs.py --since 1h
  python3 bin/logs.py --kind edge_request --status 403
  python3 bin/logs.py --kind input_blocked
  python3 bin/logs.py --request-id 3f9a...    follow one request across services
  python3 bin/logs.py --summary               counts by kind and status
"""

import argparse
import collections
import sys

from seclog import hhmmss, read_events

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="15m")
ap.add_argument("--kind")
ap.add_argument("--status", type=int)
ap.add_argument("--ip")
ap.add_argument("--request-id")
ap.add_argument("--summary", action="store_true")
ap.add_argument("--limit", type=int, default=40)
args = ap.parse_args()

events = read_events(args.since)
if args.kind:
    events = [e for e in events if e["kind"] == args.kind]
if args.status is not None:
    events = [e for e in events if e.get("status") == args.status]
if args.ip:
    events = [e for e in events if e.get("ip") == args.ip]
if args.request_id:
    events = [e for e in events if e.get("request_id", "").startswith(args.request_id)]

if not events:
    sys.exit("No matching events.")

if args.summary:
    kinds = collections.Counter(e["kind"] for e in events)
    statuses = collections.Counter(e.get("status") for e in events if e["kind"] == "edge_request")
    print(f"{len(events)} events since {args.since}\n")
    print("By kind:")
    for k, n in kinds.most_common():
        print(f"  {k:<20} {n}")
    print("\nEdge requests by status:")
    for s, n in sorted(statuses.items()):
        print(f"  {s}  {n}")
    sys.exit(0)

shown = events[-args.limit:]
if len(events) > len(shown):
    print(f"(showing the last {len(shown)} of {len(events)} events; use --limit to see more)\n")
for e in shown:
    detail = ""
    if e["kind"] in ("edge_request", "api_request", "gateway_request"):
        detail = f'user={e.get("user") or "-"} {e.get("method", "")} -> {e.get("status")}'
        if e.get("role") is not None and e["kind"] == "gateway_request":
            detail += f' role={e.get("role") or "-"}'
    elif e["kind"] in ("db_auth_failure", "db_forbidden"):
        detail = f'user={e.get("user") or "-"} {e.get("method", "")} -> {e.get("status")}'
    else:
        detail = ", ".join(e.get("reasons") or e.get("fields") or [])
        if e.get("title"):
            detail = f'"{e["title"]}" {detail}'
    rid = (e.get("request_id") or "")[:8]
    print(f'{hhmmss(e["ts"])}  {e["kind"]:<17} {e.get("ip", ""):<15} {rid:<9} {detail}')
