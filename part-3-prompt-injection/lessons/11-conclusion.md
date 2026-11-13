# Lesson 11: Conclusion

You attacked your own chatbot eight different ways, then added four layers of defense and measured each one.

---

## Your scoreboard

| Defenses on | Attacks that succeed | What changed |
|---|---|---|
| None | 7 of 8 | Every kind of attack worked |
| + Input screening | 4 of 8 | Blunt direct attacks blocked; indirect attacks untouched |
| + Prompt hardening and sanitization | 1 of 8 | Poisoned documents neutralized; wording alone made things slightly worse |
| + Output filtering | 0 of 8 (sometimes 1) | Leaked secrets withheld; attacker links and images removed |
| + Ingest screening | Poison rejected | New poisoned documents never stored; old ones found and removed |

---

## Which layer stopped which attack

| Attack | Input | Prompt | Output | Ingest |
|---|:-:|:-:|:-:|:-:|
| direct-override | ✔ | | | |
| prompt-leak | ✔ | | ✔ | |
| sneaky-leak | | | ✔ | |
| role-hijack | ✔ | | | |
| obfuscated-override | | | | |
| poisoned-link | | ✔ | ✔ | ✔ |
| image-exfiltration | | ✔ | ✔ | ✔ |
| hidden-text | | ✔ | | ✔ |

Read down any column: **no single layer stops everything.** Read across any row: most attacks are stopped by **more than one** layer, so one layer failing does not mean the attack succeeds. And one row, `obfuscated-override`, has no checkmark at all. It depends on the model.

---

## Key ideas to remember

- **Prompt injection has no complete fix.** Models cannot reliably separate instructions from data. Plan for some attacks to succeed
- **Indirect injection is the bigger threat for RAG.** The victim asks an innocent question; the attacker planted the document long before
- **Check outcomes, not just inputs.** The canary and the link allowlist catch attacks no matter how they were phrased
- **Removing beats asking.** Sanitizing documents worked; politely telling the model to ignore them did not
- **Least privilege limits the blast radius.** Even when the model was fully fooled, the read-only chat role could not change a single document
- **Measure every change, and re-run everything.** One defense made an unrelated attack more likely to succeed

---

## Going further

- **Larger models** follow security instructions more reliably. Try `OLLAMA_MODEL=llama3.2:3b` (download with `docker exec rag-ollama ollama pull llama3.2:3b`) and re-run your scoreboard
- **Classifier models** trained specifically to detect prompt injection can replace or complement the regex patterns
- **Human review** of new documents before they are indexed is the strongest ingest control for high-risk data
- **Write your own attack.** Add a case to `attacks/cases.json` that gets past all four layers. Then write the defense for it

---

## What comes next

- **Part 4: Container Hardening.** Non-root users, read-only filesystems, dropped capabilities, image scanning, and encrypted internal traffic
- **Part 5: Logging and Red-Teaming.** Turn the security events from this lab into alerts, then run a structured red-team exercise against the whole system

---

License: CC BY-SA 4.0. Jackson Holmes
