# Red Team Playbook and Rules of Engagement

Every real red-team exercise starts with a written agreement. This is the one for this lab. Read it before running `bin/redteam.py`.

---

## Rules of engagement

| | |
|---|---|
| **Target** | Your own Part 5 lab, running on your own computer |
| **Authorized by** | You (you own the system) |
| **In scope** | Everything reachable at `localhost:8088` and `localhost:7860`; the lab's Docker network; the lab's containers |
| **Out of scope** | Any other system, network, website, or person. Your computer itself outside Docker |
| **Allowed** | The 12 techniques below, as implemented in `bin/redteam.py` |
| **Not allowed** | Destroying data, disabling logging, anything that affects other people |
| **When** | Any time you choose. Note the start time so the blue team can find the activity |
| **Stop condition** | If anything unexpected happens (a crash, data loss), stop and investigate before continuing |

> Running these techniques against a system you do not own, or without written permission, is illegal in most countries, even "just to test." In a real engagement, the rules of engagement are signed by someone with authority over the target before any testing starts.

---

## Objectives

1. Find out which attacks the blue team's detections **notice**
2. Find out which attacks get through **unnoticed**
3. Produce a findings report the blue team can act on

The red team's job here is not to "win." It is to find the gaps before a real attacker does.

---

## The campaign

| Step | Technique | Attacker's goal | Expected detection |
|---|---|---|---|
| R01 | Low-and-slow injection | Test the guardrails once, quietly | D4 (it should miss: one attempt is below the threshold) |
| R02 | Reconnaissance | Learn what the service exposes without a key | D2 |
| R03 | API key brute force | Guess a valid key | D1 |
| R04 | Request flood | Degrade the service | D3 |
| R05 | Prompt injection burst | Override rules, leak the prompt, hijack the persona | D4 |
| R06 | Canary leak | Extract a secret through a normal-looking question | D5 |
| R07 | Data poisoning | Plant instructions in the knowledge base | D6 |
| R08 | Oversized payloads | Find size limits, exhaust memory | D7 |
| R09 | Schema probing | Find hidden fields such as `tenant` | D8 |
| R10 | Endpoint discovery | Find hidden admin or debug URLs with a stolen key | D9 (disabled at first) |
| R11 | Credential guessing inside the network | Log in to Milvus as root with guessed passwords from a compromised container | D10 (disabled at first) |
| R12 | Attacker inside a container | Act from inside the API container (Part 4) | None. Application logs cannot see this |

Steps R01 to R10 attack from **outside**, through the front door. R11 and R12 assume the attacker is already **inside** the Docker network, the scenario Part 4 prepared for.

---

## Severity guide for findings

| Severity | Meaning |
|---|---|
| **Critical** | An attacker could steal data, take control, or act as another user, and nobody would know |
| **High** | A serious attack would succeed or go unnoticed, but needs an extra condition (a stolen key, a foothold inside) |
| **Medium** | Unnoticed activity that usually comes before an attack (reconnaissance, probing) |
| **Low** | Minor gaps with little impact, or ones already contained by other controls |

Severity combines two things: how bad the attack is **if it works**, and how likely it is to go **unnoticed**.
