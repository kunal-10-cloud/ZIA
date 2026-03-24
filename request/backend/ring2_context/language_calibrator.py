"""
Ring 2 — Language Calibrator
==============================
Source: Architecture doc §10 Ring 2 item 5 (language calibration)
        Character Bible v2.6 §4.11 — Language Register: Mirroring the Candidate

Detects the candidate's Hinglish level from recent turns
and generates a language directive injected into Ring 2.

Four levels (Character Bible §4.11):
  Zero   — pure English, warm
  Light  — English + "na", "yaar", "achha", "theek hai"
  Medium — mixed sentences: "Suno, this is important"
  Heavy  — Hindi-dominant, English technical terms

Rules from Character Bible §4.11:
  - Start in warm English. Adapt by turn 3-4.
  - NEVER start in Hinglish.
  - Adaptation is gradual, not instant.
  - NEVER use Hindi for the first time during serious/negative moments.
"""

import re

# Hinglish detection markers (Character Bible §4.11)
HINGLISH_PARTICLES = [
    "na", "yaar", "yar", "achha", "acha", "theek hai", "theek",
    "suno", "arre", "bhai", "chal", "bas", "bilkul", "matlab",
    "samjhe", "nahi", "nhi", "haan", "han", "woh", "toh",
    "kyun", "kya", "kaisa", "kaise", "kyunki", "lekin", "aur",
    "abhi", "pehle", "baad", "bohot", "bahut", "accha",
    "thoda", "zyada", "seedha", "sab", "kuch"
]

HEAVY_HINDI_MARKERS = [
    "main", "mujhe", "tumhara", "tera", "mera", "apna", "hum",
    "kar", "karo", "karna", "dena", "lena", "aana", "jaana",
    "bolna", "sunna", "dekho", "bata", "lag", "raha", "hai",
    "tha", "thi", "the", "karunga", "karoge"
]


def detect_hinglish_level(recent_turns: list[str]) -> str:
    """
    Analyzes last 3-5 candidate turns to detect Hinglish level.

    Args:
        recent_turns: list of candidate message strings (most recent last)

    Returns:
        One of: "zero", "light", "medium", "heavy"
    """
    if not recent_turns:
        return "zero"

    combined = " ".join(recent_turns).lower()

    # Use regex to strip punctuation before word matching
    # "na?" becomes "na", "yaar," becomes "yaar" — exact match now works
    words = re.findall(r'\b\w+\b', combined)
    total_words = len(words) if words else 1

    particle_count = sum(1 for w in words if w in HINGLISH_PARTICLES)
    heavy_count = sum(1 for w in words if w in HEAVY_HINDI_MARKERS)

    particle_ratio = particle_count / total_words
    heavy_ratio = heavy_count / total_words

    if heavy_count >= 3 or heavy_ratio > 0.08:
        return "heavy"
    elif heavy_count >= 1 or particle_count >= 3:
        return "medium"
    elif particle_count >= 1:
        return "light"
    else:
        return "zero"


def generate_language_directive(
    hinglish_level: str,
    turn_number: int,
) -> str:
    """
    Converts detected Hinglish level into a Ring 2 language directive.

    Args:
        hinglish_level : "zero" | "light" | "medium" | "heavy"
        turn_number    : current turn (used to enforce "adapt by turn 3-4" rule)

    Returns:
        Language directive string for Ring 2 injection.
    """
    # Before turn 3 — always start in warm English regardless of detection
    # Character Bible §4.11: "Never start in Hinglish — always let the
    # candidate set the register first."
    if turn_number < 3:
        return (
            "--- LANGUAGE REGISTER ---\n"
            "Use warm English. Candidate's Hinglish level not yet detected. "
            "Never start in Hinglish — always let the candidate set the register first.\n"
        )

    directives = {
        "zero": (
            "--- LANGUAGE REGISTER ---\n"
            "Candidate speaks formal English. Stay in warm, confident English. "
            "No Hindi particles. Professional but not stiff.\n"
        ),
        "light": (
            "--- LANGUAGE REGISTER ---\n"
            "Candidate uses casual English with light Hindi. Mirror naturally: "
            "occasional 'na', 'yaar', 'achha' when they flow. "
            "Never force it. Gradual adaptation only.\n"
        ),
        "medium": (
            "--- LANGUAGE REGISTER ---\n"
            "Candidate actively code-switches. Match their register: "
            "mixed Hinglish sentences like 'Suno, this is important' or "
            "'Achha, toh what's the plan?' Feel natural, not performed. "
            "NEVER switch to Hinglish for the first time during serious or "
            "negative moments — only when the conversation is warm.\n"
        ),
        "heavy": (
            "--- LANGUAGE REGISTER ---\n"
            "Candidate communicates primarily in Hindi. Use Hindi-dominant "
            "speech with English technical terms. "
            "'Dekho, tumhara skillset bahut achha hai but market mein "
            "dikhta nahi.' Natural desi energy, never forced or performative.\n"
        ),
    }

    return directives.get(hinglish_level, directives["zero"])