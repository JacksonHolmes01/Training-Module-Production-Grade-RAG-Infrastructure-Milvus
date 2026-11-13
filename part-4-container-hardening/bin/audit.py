#!/usr/bin/env python3
"""
audit.py: score every running container in this lab against a
container-hardening checklist. Standard library only; uses `docker inspect`.

Usage (from the part-4-container-hardening folder):
  python3 bin/audit.py            scorecard for every container
  python3 bin/audit.py --explain  also print what each failed check means

Checks
  non-root     the container's main process does not start as root
  no-caps      every Linux capability is dropped (cap_drop: ALL)
  no-escalate  no-new-privileges is set
  read-only    the root filesystem is read-only
  no-env-keys  no secret-looking value in environment variables (a path to a
               file in /run/secrets/ is fine: it points at a secret, it is not one)
  mem-limit    a memory limit is set
  pid-limit    a process-count limit is set
  ports        no ports, or ports bound to 127.0.0.1 only
  pinned       the image is pinned by digest (image@sha256:...); for images
               built here, the Dockerfile's base image is pinned instead
"""

import json
import re
import subprocess
import sys

PROJECT_LABEL = "com.docker.compose.project"
SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL)", re.I)
# Names that look secret but are not. The official Python image sets
# GPG_KEY to the PUBLIC key fingerprint used to verify the Python download.
# MinIO's image sets MINIO_UPDATE_MINISIGN_PUBKEY to the PUBLIC key it uses
# to verify its own updates. Like GPG_KEY, it is meant to be public.
NOT_SECRET = {"GPG_KEY", "MINIO_UPDATE_MINISIGN_PUBKEY"}

EXPLAIN = {
    "non-root": "Runs as root. If an attacker gets code execution, they are root inside the container.",
    "no-caps": "Keeps Linux capabilities (e.g. CHOWN, NET_RAW, SETUID) that extend what root can do.",
    "no-escalate": "A process could gain privileges through setuid programs. Set no-new-privileges.",
    "read-only": "The filesystem is writable: an attacker can modify code or drop tools that persist until restart.",
    "no-env-keys": "A secret is in an environment variable, visible to anyone who can run `docker inspect`.",
    "mem-limit": "No memory limit: one runaway process can exhaust the host.",
    "pid-limit": "No process limit: a fork bomb can exhaust the host.",
    "ports": "A port is published on all interfaces, reachable from the network.",
    "pinned": "The image is referenced by tag only. Tags can be moved to point at different software.",
}


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def project_name():
    out = sh("docker", "compose", "config", "--format", "json")
    return json.loads(out)["name"]


def build_bases():
    """For images built from a Dockerfile, the thing to pin is the base image,
    passed in as the BASE_IMAGE build argument."""
    cfg = json.loads(sh("docker", "compose", "config", "--format", "json"))
    bases = {}
    for svc, s in cfg["services"].items():
        if "build" in s:
            bases[s.get("container_name", svc)] = (s["build"].get("args") or {}).get("BASE_IMAGE", "")
    return bases


def checks(c, bases):
    cfg, host = c["Config"], c["HostConfig"]
    user = (cfg.get("User") or "").split(":")[0]
    env = cfg.get("Env") or []
    leaked = [
        e.split("=", 1)[0] for e in env
        if "=" in e and SECRET_NAME.search(e.split("=", 1)[0])
        and e.split("=", 1)[0] not in NOT_SECRET
        and not e.split("=", 1)[0].endswith("_FILE") and e.split("=", 1)[1]
        # A path to a mounted secret file is a pointer, not the secret itself
        and not e.split("=", 1)[1].startswith("/run/secrets/")
    ]
    ports_ok = all(
        b.get("HostIp") in ("127.0.0.1", "::1")
        for bindings in (host.get("PortBindings") or {}).values() for b in (bindings or [])
    )
    image = cfg.get("Image", "")
    name = c["Name"].lstrip("/")
    if name in bases:
        image = bases[name] or "unpinned"
    return {
        "non-root": user not in ("", "0", "root"),
        "no-caps": "ALL" in [x.upper() for x in (host.get("CapDrop") or [])],
        "no-escalate": any("no-new-privileges" in s for s in (host.get("SecurityOpt") or [])),
        "read-only": bool(host.get("ReadonlyRootfs")),
        "no-env-keys": not leaked,
        "mem-limit": (host.get("Memory") or 0) > 0,
        "pid-limit": (host.get("PidsLimit") or 0) > 0,
        "ports": ports_ok,
        "pinned": "@sha256:" in image,
    }, leaked


def main():
    explain = "--explain" in sys.argv
    project = project_name()
    ids = sh("docker", "ps", "-q", "--filter", f"label={PROJECT_LABEL}={project}").split()
    if not ids:
        sys.exit(f"No running containers for project '{project}'. Start the stack first.")
    containers = json.loads(sh("docker", "inspect", *ids))
    names = list(EXPLAIN)
    bases = build_bases()

    print(f"Project: {project}\n")
    header = f"{'CONTAINER':<20}" + "".join(f"{n:>12}" for n in names) + f"{'SCORE':>8}"
    print(header)
    print("-" * len(header))
    total = passed = 0
    notes = []
    for c in sorted(containers, key=lambda c: c["Name"]):
        name = c["Name"].lstrip("/")
        result, leaked = checks(c, bases)
        ok = sum(result.values())
        total += len(result)
        passed += ok
        print(f"{name:<20}" + "".join(f"{('pass' if result[n] else 'FAIL'):>12}" for n in names) + f"{ok:>6}/{len(result)}")
        for n in names:
            if not result[n]:
                extra = f" ({', '.join(leaked)})" if n == "no-env-keys" else ""
                notes.append(f"  {name}: {n}{extra}: {EXPLAIN[n]}")
    print("-" * len(header))
    print(f"Total: {passed} of {total} checks pass ({100 * passed // total}%)")
    if explain and notes:
        print("\nWhat failed and why it matters:")
        print("\n".join(notes))


if __name__ == "__main__":
    main()
