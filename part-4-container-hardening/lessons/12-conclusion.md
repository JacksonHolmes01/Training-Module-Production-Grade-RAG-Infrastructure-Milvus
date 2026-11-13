# Lesson 12: Conclusion

You took seven containers from 34% to 100% on a hardening audit, watched an attacker's options shrink from everything to nothing, and kept the whole system working at every step.

---

## What each layer bought you

| Layer | Setting | Stops |
|---|---|---|
| 1 Non-root | `user:`, unprivileged NGINX image, read-only models | Code changes, package installs, privileged operations, model tampering |
| 2 Capabilities | `cap_drop: [ALL]`, `no-new-privileges`, `pids_limit` | Regaining root through setuid programs or kernel bugs; fork bombs |
| 3 Read-only | `read_only: true`, `tmpfs` with `noexec` | Dropping and running tools; anything surviving a restart |
| 4 Secrets | `_FILE` variables, mounted secret files | Keys leaking through `docker inspect`, `env`, crash dumps |
| 5 Internal TLS | Milvus serves HTTPS only; the API trusts only the lab CA and checks the hostname | Reading or impersonating the database from inside the network |
| 6 Pinned images | `image@sha256:...`, scanned first | Running software that changed without you knowing; shipping known CVEs unknowingly |

---

## Key ideas to remember

- **Assume something will get in.** Hardening is about the second step: what the attacker can do once inside
- **Least privilege applies to processes, not just people.** Every service ran as root until you said otherwise
- **"Running" is not "working."** NGINX reported Up while serving nothing. Only end-to-end tests catch that
- **Change one thing, test everything.** Every layer in this lab broke something the first time it was built
- **Use several kinds of evidence.** The audit, the attacker demo, `/proc/1/status`, and the plain-HTTP test each saw things the others missed
- **Scanning is a snapshot.** New vulnerabilities appear daily. Pin what you scanned, then update on purpose

---

## Going further

- **Distroless or minimal base images** (no shell, no package manager) leave an attacker almost nothing to work with. Try rebuilding the API on one and re-run the attacker demo
- **Seccomp and AppArmor profiles** restrict which system calls a container may make, going beyond capabilities
- **Rootless Docker** runs the Docker engine itself without root on the host
- **Signed images** (with tools like Cosign) let you verify **who** built an image, not just that it has not changed
- **Scan in CI**: run `bin/scan_images.sh` on every change and fail the build on new critical findings

---

## What comes next

**Part 5: Logging and Red-Teaming.** You now have security events from Part 3 and a hardened system from Part 4. Part 5 turns those events into alerts, adds audit logging across the stack, and ends with a structured red-team exercise against everything you have built.

---

License: CC BY-SA 4.0. Jackson Holmes
