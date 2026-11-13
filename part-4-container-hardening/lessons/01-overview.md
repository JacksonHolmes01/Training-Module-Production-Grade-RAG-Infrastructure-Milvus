# Lesson 1: Why Harden Containers?

## The question Part 4 answers

Lab 1 and Part 3 controlled who can **talk to** the system: API keys, database roles, a gateway, prompt injection guards.

Part 4 asks a different question:

> **If an attacker gets code running inside one of the containers anyway, how much damage can they do?**

That is not a far-fetched scenario. It happens through:
- a vulnerable library (a bug in a JSON parser, an image library, a web framework)
- a malicious package that slipped into a dependency
- a compromised base image
- a mistake in your own code

You cannot guarantee none of these will ever happen. You **can** make sure that when one does, the attacker lands in a small, locked room instead of a house with every door open.

---

## What "locked room" means

| Control | Without it, an attacker inside the container can... |
|---|---|
| **Non-root user** | Act as root: change any file, install software, use every privilege the container has |
| **No capabilities** | Use Linux "superpowers" such as changing file ownership or crafting raw network packets |
| **No privilege escalation** | Become root again through a setuid program, even after starting as a normal user |
| **Process limit** | Start thousands of processes and freeze the host (a "fork bomb") |
| **Read-only filesystem** | Rewrite the application's code with a backdoor, or drop hacking tools on disk |
| **No secrets in environment variables** | Read keys from the environment, and so can anyone who runs `docker inspect` |
| **Encrypted internal traffic** | Read or alter traffic between services if they get onto the network |
| **Scanned, pinned images** | (Before any of this) start from software with known holes, or software that changed without you noticing |

None of these stop the first bug. They limit what the bug is worth.

---

## How Part 4 works

The same measure-then-fix method as Part 3:

1. **Audit** every container against a 9-point checklist (`bin/audit.py`)
2. **Attack**: pretend to be an attacker inside the API container and see what works (`bin/attacker_demo.sh`)
3. **Harden one layer at a time** with `bin/harden.sh`, re-auditing after each
4. **Prove nothing broke**: smoke test and the Part 3 attack suite after every layer

The six hardening layers live in `hardening/`, one small file each. You will read every line before you apply it.

| Layer | File | Lesson |
|---|---|---|
| 1 | `01-non-root.yml` | 5 |
| 2 | `02-capabilities.yml` | 6 |
| 3 | `03-read-only.yml` | 7 |
| 4 | `04-secrets.yml` | 8 |
| 5 | `05-internal-tls.yml` | 9 |
| 6 | `06-pinned.yml` (you generate it) | 10 |

---

## A word on trade-offs

Every layer in this part broke something the first time it was tried while building this lab. You will see each of those failures and their fixes. Hardening is not "add a setting and walk away." It is **change one thing, test everything, repeat**.

Next: [Setup](02-setup.md)
