#!/usr/bin/env python3
"""
detect.py: apply the rules in detections/rules.json to the recent logs and
print any alerts.

Usage (from the part-5 folder):
  python3 bin/detect.py               last 15 minutes
  python3 bin/detect.py --since 1h
  python3 bin/detect.py --rules       list every rule and whether it is enabled
  python3 bin/detect.py --explain     also print why each alert matters and what to do
  python3 bin/detect.py --enable D9   turn a rule on  (edits detections/rules.json)
  python3 bin/detect.py --disable D9  turn a rule off
"""

import argparse
import json

from seclog import ROOT, detect, hhmmss, load_rules, read_events

ap = argparse.ArgumentParser()
ap.add_argument("--since", default="15m")
ap.add_argument("--rules", action="store_true")
ap.add_argument("--explain", action="store_true")
ap.add_argument("--enable", metavar="ID")
ap.add_argument("--disable", metavar="ID")
args = ap.parse_args()

if args.enable or args.disable:
    path = ROOT / "detections" / "rules.json"
    rules = json.loads(path.read_text())
    target = (args.enable or args.disable).upper()
    for r in rules:
        if r["id"] == target:
            r["enabled"] = bool(args.enable)
            path.write_text(json.dumps(rules, indent=2) + "\n")
            print(f'{target} "{r["name"]}" is now {"enabled" if args.enable else "disabled"}.')
            raise SystemExit(0)
    raise SystemExit(f"No rule with id {target}.")

if args.rules:
    print(f"{'ID':<5} {'ON':<4} {'SEVERITY':<9} {'RULE':<32} FIRES WHEN")
    for r in load_rules(include_disabled=True):
        m = r["match"]
        what = m["kind"] + (f' status {m["status"]}' if "status" in m else "")
        print(f'{r["id"]:<5} {"yes" if r.get("enabled", True) else "no":<4} {r["severity"]:<9} {r["name"]:<32} '
              f'{r["threshold"]}+ {what} from one {r.get("group_by", "ip")} in {r["window_s"]}s')
    raise SystemExit(0)

alerts = detect(read_events(args.since), load_rules())
if not alerts:
    print(f"No alerts in the last {args.since}.")
    raise SystemExit(0)

print(f"{'TIME':<9} {'SEVERITY':<9} {'RULE':<5} {'ALERT':<32} {'SOURCE':<15} COUNT")
for a in alerts:
    print(f'{hhmmss(a["time"]):<9} {a["severity"].upper():<9} {a["rule"]:<5} {a["name"]:<32} {a["group"]:<15} {a["count"]}')
    if args.explain:
        print(f'          why:      {a["why"]}')
        print(f'          response: {a["response"]}')
print(f"\n{len(alerts)} alert(s) in the last {args.since}.")
