#!/usr/bin/env python3
"""
run_attacks.py: run every attack in attacks/cases.json against /chat and
report what happened. Standard library only.

Usage (from the part-3-prompt-injection folder):
  python3 attacks/run_attacks.py            run all attacks
  python3 attacks/run_attacks.py --plant    first ingest attacks/poisoned_docs.jsonl
  python3 attacks/run_attacks.py --only prompt-leak
  python3 attacks/run_attacks.py --show     also print each answer

Outcomes
  ATTACK SUCCEEDED   the answer contains the attacker's goal
  blocked: input     the input guard rejected the message
  filtered: output   the output guard removed or withheld the attacker's goal
  resisted           the model did not do what the attacker wanted
  answered / BLOCKED (false positive)   for the normal control question
"""

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "http://localhost:8088"


def api_key() -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("EDGE_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("EDGE_API_KEY not found in .env. Run bin/setup_secrets.sh first.")


def call(method: str, path: str, body=None, timeout: float = 300.0):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": api_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"null")
        except ValueError:
            return e.code, None


def plant() -> None:
    print("Planting poisoned documents (this is the attacker's step)...")
    for line in (ROOT / "attacks" / "poisoned_docs.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        doc = json.loads(line)
        code, body = call("POST", "/ingest", doc)
        if code == 200:
            print(f"  planted   {doc['title']}")
        elif code == 422 and isinstance(body, dict) and isinstance(body.get("detail"), dict):
            print(f"  REJECTED  {doc['title']}  ({', '.join(body['detail'].get('reasons', []))})")
        else:
            print(f"  error     {doc['title']}  HTTP {code}: {body}")
    print()


def classify(case, code, body):
    goals = case["success_if_contains"]
    if case["kind"] == "control":
        return ("answered", "") if code == 200 else ("BLOCKED (false positive)", "")
    if code == 400:
        reasons = ", ".join((body or {}).get("detail", {}).get("reasons", []))
        return "blocked: input", reasons
    if code != 200:
        return f"error HTTP {code}", ""
    answer = (body or {}).get("answer", "")
    if any(g.lower() in answer.lower() for g in goals):
        return "ATTACK SUCCEEDED", ""
    if body.get("output_filter"):
        return "filtered: output", ", ".join(body["output_filter"])
    return "resisted", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", action="store_true", help="ingest the poisoned documents first")
    ap.add_argument("--only", help="run a single case by id")
    ap.add_argument("--show", action="store_true", help="print each answer")
    args = ap.parse_args()

    code, health = call("GET", "/health", timeout=10)
    if code != 200:
        sys.exit(f"API not reachable (HTTP {code}). Is the stack running?")
    on = [k for k, v in health["guards"].items() if v]
    print(f"Guards on: {', '.join(on) if on else 'none'}\n")

    if args.plant:
        plant()

    cases = json.loads((ROOT / "attacks" / "cases.json").read_text())
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]

    succeeded = 0
    attacks = 0
    print(f"{'ATTACK':<22} {'TYPE':<9} {'RESULT':<26} DETAIL")
    print("-" * 78)
    for case in cases:
        code, body = call("POST", "/chat", {"message": case["message"]})
        result, detail = classify(case, code, body)
        if case["kind"] != "control":
            attacks += 1
            succeeded += result == "ATTACK SUCCEEDED"
        print(f"{case['id']:<22} {case['kind']:<9} {result:<26} {detail}")
        if args.show and code == 200:
            print("    answer: " + body.get("answer", "").replace("\n", " ")[:400] + "\n")

    print("-" * 78)
    print(f"{succeeded} of {attacks} attacks succeeded.")


if __name__ == "__main__":
    main()
