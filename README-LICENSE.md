<!--
License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
Author: Jackson Holmes
https://creativecommons.org/licenses/by-sa/4.0/
-->

# Licensing — Lab 1: Production-Grade RAG Infrastructure with Milvus

This repository contains two distinct types of content — code and educational material — each covered by a different license. This document explains what each license means, which files it applies to, and what you are and are not permitted to do.

---

## Overview

| Content Type | License | Applies To |
|---|---|---|
| Source code | MIT | Python files, shell scripts, Docker configs |
| Educational content | CC BY-SA 4.0 | Lessons, docs, quizzes, slides, podcasts |

---

## Part 1 — Source Code: MIT License

### What is the MIT License?

The MIT License is one of the most permissive open source licenses. It allows anyone to use, copy, modify, merge, publish, distribute, sublicense, and sell copies of the software with minimal restrictions. The only requirement is that the original copyright notice and license text are included in any copies or substantial portions of the software.

### What does this mean for you?

You are free to:
- Use the code in your own projects, commercially or non-commercially
- Modify the code however you like
- Distribute your modified version to others
- Include the code in a larger project under a different license

You must:
- Include the original MIT license text and copyright notice in any copy or redistribution

You are not required to:
- Share your modifications publicly
- Credit the author in your application's UI (only in the license file itself)
- Use the same license for derivative works

### Which files are covered by MIT?

- All Python source files (`*.py`) including `main.py`, `rag.py`, `schemas.py`, `milvus_client.py`, `db.py`, `store.py`, `router.py`, `ingest.py`, and all others in `ingestion-api/`
- All shell scripts (`*.sh`) in `bin/`
- `docker-compose.yml`
- `.env.example`
- All `Dockerfile` files
- NGINX configuration templates in `nginx/templates/`
- `requirements.txt`

### MIT License Text

```
MIT License

Copyright (c) 2025 Jackson Holmes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Part 2 — Educational Content: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

### What is CC BY-SA 4.0?

Creative Commons Attribution-ShareAlike 4.0 is a standard license designed for creative and educational works. It is widely used by educators, universities, and open courseware programs including MIT OpenCourseWare and Wikipedia.

The two key requirements are:

**Attribution (BY):** If you use, share, or adapt this material, you must give appropriate credit to the original author, provide a link to the license, and indicate if changes were made.

**ShareAlike (SA):** If you remix, transform, or build upon this material, you must distribute your contributions under the same CC BY-SA 4.0 license. You cannot take this material, adapt it, and release it under a more restrictive license or make it proprietary.

### What does this mean for you as a student?

You are free to:
- Read, download, and use all educational content for learning
- Share the material with others (with attribution)
- Adapt and build upon the material — for example, translate lessons, add new exercises, or create study guides based on this content
- Use the material in your own educational projects

You must:
- Credit the original author (Jackson Holmes) when sharing or adapting
- Include a link to the CC BY-SA 4.0 license
- Release any adapted versions under the same CC BY-SA 4.0 license — you cannot make derivative educational works proprietary

You cannot:
- Remove the author's name and republish the material as your own original work
- Adapt the material and release it under a more restrictive license
- Use technological measures (DRM) to restrict others from doing what the license permits

### What does this mean for instructors or others using this material?

If you are an instructor who wants to use these lessons, quizzes, or documentation in your own course:
- You may use and adapt them freely with attribution
- Your adapted version must also be CC BY-SA 4.0 — you cannot incorporate this material into proprietary course content
- A citation like "Adapted from Jackson Holmes, Lab 1: Production-Grade RAG Infrastructure with Milvus, CC BY-SA 4.0" satisfies the attribution requirement

### Which files are covered by CC BY-SA 4.0?

**Lesson files:**
- All files in `lessons/` including the core lessons (01–10) and the security memory extension (`lessons/04-security-memory/`)
- All lessons and READMEs in `part-3-prompt-injection/`, `part-4-container-hardening/`, and `part-5-logging-red-team/`, including `redteam/PLAYBOOK.md`

**Documentation and README files:**
- `README.md`
- `Advanced-ReadME.md`
- `README_INTEGRATION.md`
- `Docker_Architecture.md`
- `Building_Your_Own_Docker_Images.md`
- All `.md` files in `security-memory/docs/`

**Security memory educational content:**
- All files in `security-memory/prompts/`
- All files in `security-memory/docs/`
- `security-memory/slides/slide_outline.md`

### CC BY-SA 4.0 License Summary

```
Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

Copyright (c) 2025 Jackson Holmes

You are free to:
  Share — copy and redistribute the material in any medium or format
  Adapt — remix, transform, and build upon the material for any purpose

Under the following terms:
  Attribution — You must give appropriate credit, provide a link to the
  license, and indicate if changes were made.

  ShareAlike — If you remix, transform, or build upon the material, you
  must distribute your contributions under the same license as the original.

Full license text: https://creativecommons.org/licenses/by-sa/4.0/legalcode
```

---

## Questions

If you are unsure whether your intended use of any material in this repository is permitted under these licenses, refer to:

- MIT License full text: https://opensource.org/licenses/MIT
- CC BY-SA 4.0 full text: https://creativecommons.org/licenses/by-sa/4.0/legalcode

---

*This document is itself licensed under CC BY-SA 4.0 — Jackson Holmes, 2025*
