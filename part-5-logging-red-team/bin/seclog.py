"""
seclog.py: shared code for reading this lab's logs and applying detection rules.
Standard library only. Used by bin/logs.py, bin/detect.py, and bin/coverage.py.

Every log line is turned into one "event" dictionary:
  {"ts": datetime, "source": ..., "kind": ..., "ip": ..., "status": ..., ...}

Kinds
  edge_request       one request seen by the NGINX edge (JSON access log)
  api_request        one request handled by the API (JSON access log)
  input_blocked, output_blocked, output_filtered, document_blocked,
  validation_error   security events written by the API
  db_auth_failure    a request to Milvus with a missing or wrong password (HTTP 401)
  db_forbidden       a valid Milvus user tried something its role does not allow (HTTP 403)
  gateway_request    one request seen by the internal Chroma gateway (Chroma labs)
"""

import json
import pathlib
import re
import subprocess
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Docker prefixes each line: "<container>  | <timestamp> <message>"
LINE = re.compile(r"^(?P<container>[\w.-]+)\s+\|\s+(?P<ts>\d{4}-\d\d-\d\dT[\d:.]+Z)\s(?P<msg>.*)$")
# Milvus's access log: [<time>] [ACCESS] <user: ip> <method> [status: <status>] ...
MILVUS_ACCESS = re.compile(r'\[ACCESS\]\s+<(?P<user>[^:>]*):\s*(?P<ip>[^>]*)>\s+(?P<method>\S+)\s+\[status:\s*(?P<status>[^\]]+)\]')
MILVUS_KINDS = {"HttpError401": "db_auth_failure", "HttpError403": "db_forbidden"}


def _ts(text: str) -> datetime:
    text = text.rstrip("Z")
    if "." in text:
        head, frac = text.split(".", 1)
        text = f"{head}.{frac[:6]}"
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def services() -> list:
    out = subprocess.run(["docker", "compose", "config", "--services"],
                         capture_output=True, text=True, cwd=ROOT, check=True).stdout.split()
    wanted = ["nginx", "ingestion-api", "milvus", "pgvector", "chroma-gateway"]
    return [s for s in wanted if s in out]


def read_events(since: str = "1h") -> list:
    """Collect events from docker compose logs. `since` is like 10m, 1h, or an ISO time."""
    raw = subprocess.run(
        ["docker", "compose", "logs", "--no-color", "--timestamps", "--since", since, *services()],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout
    events = []
    for line in raw.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        ts, msg, container = _ts(m["ts"]), m["msg"].strip(), m["container"]
        ev = None
        if msg.startswith("{"):
            try:
                data = json.loads(msg)
            except ValueError:
                data = None
            if isinstance(data, dict):
                if data.get("source") == "edge":
                    ev = {"kind": "edge_request", **data}
                elif data.get("source") == "gateway":
                    ev = {"kind": "gateway_request", **data}
                elif data.get("event") == "request":
                    ev = {"kind": "api_request", **data}
                elif "security_event" in data:
                    ev = {"kind": data["security_event"], **data}
        else:
            qm = MILVUS_ACCESS.search(msg)
            # Only refusals are security events; Milvus's normal traffic is not
            if qm and qm["status"].strip() in MILVUS_KINDS:
                status = qm["status"].strip()
                ev = {"kind": MILVUS_KINDS[status], "source": "milvus", "ip": qm["ip"].strip(),
                      "user": qm["user"].strip(), "method": qm["method"], "status": int(status[-3:])}
        if ev is not None:
            ev["ts"] = ts
            ev["container"] = container
            events.append(ev)
    events.sort(key=lambda e: e["ts"])
    return events


def load_rules(include_disabled: bool = False) -> list:
    rules = json.loads((ROOT / "detections" / "rules.json").read_text())
    return [r for r in rules if include_disabled or r.get("enabled", True)]


def _matches(ev: dict, match: dict) -> bool:
    for key, want in match.items():
        have = ev.get(key)
        if isinstance(want, list):
            if have not in want:
                return False
        elif have != want:
            return False
    return True


def detect(events: list, rules: list) -> list:
    """Sliding-window threshold detection.
    An alert fires when `threshold` matching events from the same group arrive
    within `window_s` seconds. After firing, that rule stays quiet for that
    group for one window, so one attack produces one alert, not hundreds."""
    alerts = []
    for rule in rules:
        window = timedelta(seconds=rule["window_s"])
        recent = defaultdict(deque)
        quiet_until = {}
        for ev in events:
            if not _matches(ev, rule["match"]):
                continue
            group = str(ev.get(rule.get("group_by", "ip"), "") or "-")
            q = recent[group]
            q.append(ev)
            while q and ev["ts"] - q[0]["ts"] > window:
                q.popleft()
            if len(q) >= rule["threshold"] and ev["ts"] >= quiet_until.get(group, ev["ts"]):
                alerts.append({
                    "time": ev["ts"], "rule": rule["id"], "name": rule["name"],
                    "severity": rule["severity"], "group": group, "count": len(q),
                    "first": q[0]["ts"], "request_id": ev.get("request_id", ""),
                    "why": rule["why"], "response": rule["response"],
                })
                quiet_until[group] = ev["ts"] + window
                q.clear()
    alerts.sort(key=lambda a: a["time"])
    return alerts


def hhmmss(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%H:%M:%S")
