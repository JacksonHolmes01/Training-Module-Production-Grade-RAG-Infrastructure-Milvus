# Lesson 11: Conclusion

You attacked your own system with twelve techniques, measured what your defenses noticed, closed two gaps, and wrote down the two that remain, along with why.

---

## Part 5 in one table

| What you built | What it gives you |
|---|---|
| Structured JSON logs at the edge and API, plus Milvus's access log | Every request and security decision, searchable |
| A request id across services | One request's full story from one id |
| Ten detection rules with `why` and `response` | Alerts a person can act on |
| A scripted, timestamped red-team campaign | Repeatable, measurable attacks |
| Detection coverage scoring | A number to improve, not a feeling |
| A findings report | Decisions someone can make |

| Coverage | |
|---|---|
| Initial | 8 of 12 (66%) |
| After enabling D9 and D10 | 10 of 12 (83%) |
| Remaining | R01 (a tuning problem) and R12 (a visibility problem) |

---

## The whole series

| Part | Question it answered | Key idea |
|---|---|---|
| 1 | Who can reach the data? | Test that bad requests **fail** |
| 2 | How do the pieces trust each other? | The most exposed component gets the least power |
| 3 | Can the AI be talked into misbehaving? | Layered defenses, each **measured** |
| 4 | If an attacker gets in, how far can they go? | Assume breach; limit the blast radius |
| 5 | Will we know when it happens? | Detection coverage, and honest blind spots |

The method never changed: **attack it, measure it, fix one thing, measure again.**

---

## Key ideas to remember

- **Prevention fails eventually; detection decides how bad it gets**
- **Log what happened and why, not the content.** Logs must not become a second copy of every secret and every private question
- **Logging without detection feels like coverage but is not.** Two disabled rules hid two serious attacks
- **Write the expected detection before you attack.** Otherwise any result looks like success
- **Tuning moves blind spots.** Re-measure everything after every change
- **Every log source has a field of view.** Know what yours cannot see

---

## Going further

- **Ship logs centrally**: run Grafana Loki or OpenSearch alongside the lab and point Docker's logging driver at it
- **Alert in real time**: run `bin/detect.py` every minute and post alerts to a chat channel
- **Add runtime security**: install Falco on a Linux host and write the "only uvicorn may run in rag-api" rule
- **Map to a framework**: label each red-team step with its MITRE ATT&CK technique and each AI-specific one with OWASP's Top 10 for LLM Applications
- **Invite a real red team**: give a classmate the playbook and the lab's address, and see what **they** find that your script did not

---

Thank you for working through the series.

License: CC BY-SA 4.0. Jackson Holmes
