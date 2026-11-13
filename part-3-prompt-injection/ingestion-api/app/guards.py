"""
guards.py: prompt injection defenses.

Four independent layers, each switched on or off in .env so you can
measure what each one stops:

  GUARD_INPUT    screen the user's chat message before anything else runs
  GUARD_INGEST   screen documents before they are stored
  GUARD_PROMPT   build a hardened prompt that separates rules from data
                 (see rag.py)
  GUARD_OUTPUT   check the model's answer before it reaches the user:
                 block leaked secrets, strip untrusted links and images

None of these is perfect on its own. Pattern matching can be evaded and
models can be talked around. The point is layers: each one catches some
of what the others miss.
"""

import os
import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple
from urllib.parse import urlparse


def _flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() == "true"


GUARD_INPUT  = _flag("GUARD_INPUT")
GUARD_INGEST = _flag("GUARD_INGEST")
GUARD_PROMPT = _flag("GUARD_PROMPT")
GUARD_OUTPUT = _flag("GUARD_OUTPUT")

ALLOWED_LINK_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("ALLOWED_LINK_DOMAINS", "example.org").split(",")
    if d.strip()
}

# A random value placed in the system prompt. It is never shown to users,
# so if it ever appears in an answer, the prompt has leaked.
CANARY = "INTERNAL-REF-" + secrets.token_hex(6).upper()


# -------------------------------------------------------------------
# Normalization: undo common disguises before matching
# -------------------------------------------------------------------
# Zero-width and other invisible characters can hide text from humans
# while the model still reads it, or split words so patterns miss them.
_INVISIBLE = re.compile("[​‌‍⁠⁣﻿­]")


def has_invisible_chars(text: str) -> bool:
    return bool(_INVISIBLE.search(text))


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)   # fold look-alike characters
    text = _INVISIBLE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


# -------------------------------------------------------------------
# Injection patterns: (regex, weight, label)
# Weights add up; a message is blocked when its score reaches a threshold.
# -------------------------------------------------------------------
PATTERNS: List[Tuple[re.Pattern, int, str]] = [(re.compile(p), w, l) for p, w, l in [
    (r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|any|your|the)\b.{0,20}\b(instructions?|rules?|prompts?|guidelines?|directions?)\b", 3, "override-instructions"),
    (r"\b(reveal|show|print|repeat|output|display|tell me|what (is|are))\b.{0,30}\b(system prompt|your (instructions|rules|prompt)|hidden (instructions|prompt|text)|everything above|internal (reference|code|note)s?)\b", 3, "prompt-extraction"),
    (r"\b(you are now|from now on,? you|act as|pretend (to be|you are)|roleplay as|jailbreak|developer mode|\bdan\b)", 2, "role-hijack"),
    (r"\b(no|without( any)?|free of)\b.{0,10}\b(rules|restrictions|limits|filters|guidelines|guardrails)\b", 2, "rule-removal"),
    (r"(^|\s)(system|assistant)\s*:|<\|im_start\|>|\[/?inst\]|###\s*(instruction|system)|<<\s*sys\s*>>", 2, "fake-role-marker"),
    (r"\b(new|updated|important|secret|hidden)\b.{0,15}\b(instructions?|system (note|message|override))\b", 2, "injected-instruction-header"),
    (r"\b(note to|attention|instructions? (for|to))\b.{0,20}\b(ai|assistant|model|llm|chatbot)\b", 3, "addressed-to-ai"),
    (r"\b(when|if|whenever)\b.{0,20}\b(user|anyone|someone|they)\b.{0,10}\b(asks?|questions?|requests?)\b", 2, "conditional-trigger"),
    (r"\b(do not|don't|never)\b.{0,15}\b(tell|mention|reveal|inform)\b.{0,15}\b(the user|users|anyone)\b", 2, "concealment"),
    (r"!\[[^\]]*\]\(\s*https?://", 3, "markdown-image"),
    (r"\b(send|email|post|forward|submit)\b.{0,40}\b(password|credentials?|api key|token|secret)s?\b", 2, "credential-exfiltration"),
]]

INPUT_THRESHOLD = int(os.getenv("GUARD_INPUT_THRESHOLD", "3"))
# Documents should describe things, not give orders to an AI, so the bar is lower.
DOC_THRESHOLD = int(os.getenv("GUARD_DOC_THRESHOLD", "2"))


@dataclass
class Verdict:
    blocked: bool
    score: int
    reasons: List[str] = field(default_factory=list)


def _score(text: str) -> Verdict:
    norm = normalize(text)
    reasons, score = [], 0
    for rx, weight, label in PATTERNS:
        if rx.search(norm):
            reasons.append(label)
            score += weight
    if has_invisible_chars(text):
        reasons.append("invisible-characters")
        score += 2
    return Verdict(False, score, reasons)


def screen_input(message: str) -> Verdict:
    v = _score(message)
    v.blocked = GUARD_INPUT and v.score >= INPUT_THRESHOLD
    return v


def screen_document(text: str) -> Verdict:
    v = _score(text)
    v.blocked = GUARD_INGEST and v.score >= DOC_THRESHOLD
    return v


def screen_sentence(sentence: str) -> bool:
    """True if one sentence of a retrieved document looks like an
    instruction to the AI (used by the hardened prompt)."""
    return _score(sentence).score >= DOC_THRESHOLD


# -------------------------------------------------------------------
# Output filtering
# -------------------------------------------------------------------
_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]+)[^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)[^)]*\)")
_BARE_URL = re.compile(r"(?<![\(\[])\bhttps?://[^\s)\]>\"']+", re.I)


def _allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED_LINK_DOMAINS)


@dataclass
class OutputCheck:
    text: str
    blocked: bool
    reasons: List[str] = field(default_factory=list)


def filter_output(answer: str) -> OutputCheck:
    reasons: List[str] = []

    # Contains the canary in any form (case, spacing, or invisible chars changed)?
    # Small models sometimes copy only PART of the code (INTERNAL-REF-6E6C9888).
    # That is still a leak, so the marker followed by any hex digits counts too.
    squashed = re.sub(r"[\s\-_]", "", normalize(answer))
    marker = re.sub(r"[\s\-_]", "", CANARY.rsplit("-", 1)[0].lower())
    if (re.sub(r"[\s\-_]", "", CANARY.lower()) in squashed
            or re.search(marker + r"[0-9a-f]{4,}", squashed)):
        return OutputCheck(
            "I can't share that. (The response was withheld because it contained internal configuration.)",
            True,
            ["canary-leak"],
        )

    # Images load automatically in the browser, so an image URL can carry
    # data to an attacker with no click at all. Remove every image.
    def drop_image(m):
        reasons.append("image-removed")
        return f"[image removed: {m.group(1) or 'untitled'}]"
    text = _MD_IMAGE.sub(drop_image, answer)

    def check_link(m):
        if _allowed(m.group(2)):
            return m.group(0)
        reasons.append("link-removed")
        return f"{m.group(1)} [link removed]"
    text = _MD_LINK.sub(check_link, text)

    def check_bare(m):
        if _allowed(m.group(0)):
            return m.group(0)
        reasons.append("link-removed")
        return "[link removed]"
    text = _BARE_URL.sub(check_bare, text)

    return OutputCheck(text, False, sorted(set(reasons)))


def status() -> dict:
    return {
        "input": GUARD_INPUT,
        "ingest": GUARD_INGEST,
        "prompt": GUARD_PROMPT,
        "output": GUARD_OUTPUT,
    }
