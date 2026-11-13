# Lesson 10: Writing the Report

The exercise is not finished when the attacks are. It is finished when someone who was not there can read what happened and decide what to fix.

---

## Generate a draft

```bash
python3 bin/coverage.py --report
```

```
Report draft written to redteam/report-20261112-183112.md
```

Open the file. It has:

| Section | Contents |
|---|---|
| **Summary** | When the campaign ran, coverage, number of alerts |
| **Results by step** | What each attack did, what the attacker saw, whether it was detected |
| **Findings** | One section per **undetected** step, with the detection gap already identified |
| **Alerts raised** | Every alert, with time, severity, and rule |
| **Sign-off** | Who ran it, who reviewed it |

It is a **draft**. A tool can list facts; it cannot judge risk or recommend fixes. That is your part.

---

## Complete each finding

For each finding, fill in **Severity** and **Recommendation** using the severity guide in `redteam/PLAYBOOK.md`.

Here is a worked example for R12:

> ### R12: Attacker inside a container
>
> - **Technique:** Run commands inside the API container (Part 4's demo)
> - **What happened:** commands inside rag-api -> ['ok', 'blocked', 'blocked', 'ok']
> - **Detection gap:** no rule covers this. The logs this lab collects cannot see it.
> - **Severity:** High. Part 4's hardening blocked code changes and package installs, so the impact was contained. But an attacker with a foothold could keep probing indefinitely with zero visibility, and the next weakness they find would also go unnoticed.
> - **Recommendation:** Deploy runtime security monitoring (for example Falco) with a rule alerting on any process other than `uvicorn` starting in `rag-api`. Until then, accept the risk explicitly and review it quarterly.

And one for R01:

> ### R01: Low-and-slow injection
>
> - **Detection gap:** rule D4 "Prompt injection probing" is enabled but did not fire.
> - **Severity:** Medium. The injection was blocked, and the event was logged. Only the alert was missing.
> - **Recommendation:** Add a daily low-severity rule (1 `input_blocked` per 24 hours) feeding a daily review, rather than lowering D4's threshold, which was shown to hide follow-up bursts.

Notice how each recommendation is **specific** (which rule, which tool, which threshold) and **cites evidence** from the exercise (the threshold experiment in Lesson 8).

---

## What makes a good findings report

- **Facts first, then judgment.** What happened, then what it means
- **Separate "attack succeeded" from "attack went unnoticed."** In this campaign every attack failed, yet two went unnoticed. Both matter
- **Every finding gets an owner and a fix**, or an explicit decision to accept the risk
- **Re-test.** A finding is closed when a re-run of the campaign shows it detected, not when someone says it is fixed

---

## Close the loop

Run the campaign again with D9 and D10 enabled, and confirm the improvements hold on a fresh run, not just a re-score:

```bash
python3 bin/redteam.py
python3 bin/coverage.py
```

```
Detection coverage: 10 of 12 attack steps (83%)
```

Next: [Conclusion](11-conclusion.md)
