# Lesson 6: Planning the Red Team

A red-team exercise is not "attack things and see what happens." It starts with a plan everyone agrees to in advance.

---

## Read the playbook

Open `redteam/PLAYBOOK.md`. It has three parts.

### 1. Rules of engagement

What may be tested, by whom, when, and what is off limits. In a real engagement this is signed before any testing begins. Testing without it, even with good intentions, can be a crime.

Notice the **stop condition**: if something unexpected happens, stop. A red team that breaks production has failed, even if it found a real weakness.

### 2. The campaign

Twelve steps, each with a goal and an **expected detection**. Writing the expected detection down **before** attacking is what makes the result measurable. Otherwise it is easy to look at whatever alerts appeared and declare success.

Two steps are expected to be missed:
- **R01** (one quiet injection attempt) sits below D4's threshold of 2
- **R12** (an attacker inside a container) produces no application logs at all

Predicting your own blind spots is part of the job.

### 3. Severity guide

How to rate each finding in the report: how bad if it works, and how likely to go unnoticed.

---

## See the steps

```bash
python3 bin/redteam.py --list
```

```
R01  Low-and-slow injection         A single prompt injection attempt, staying under alert thresholds
R02  Reconnaissance                 Map the API without a key
R03  API key brute force            Guess API keys
R04  Request flood                  Overwhelm the service
R05  Prompt injection burst         Override, leak, and role-hijack attempts
R06  Canary leak                    Leak the system prompt's secret through a normal-looking question
R07  Data poisoning                 Plant documents that carry instructions for the AI
R08  Oversized payloads             Send requests larger than allowed
R09  Schema probing                 Send unexpected fields, including a 'tenant' override
R10  Endpoint discovery             Guess hidden admin and debug URLs with a stolen key
R11  Database credential guessing   From inside the network, guess Milvus's root password
R12  Attacker inside a container    Run commands inside the API container (Part 4's demo)
```

Open `bin/redteam.py` and read at least three of the step functions. Each is a few lines and does exactly what a real attacker's script would do.

---

## Make a prediction

Before running anything, write down in your notes:
1. How many of the 12 steps do you expect to be detected?
2. Which ones will be missed, and why?

You will compare your prediction with the result in the next lesson.

Next: [Running the Campaign](07-campaign.md)
