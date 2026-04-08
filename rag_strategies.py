"""
RAG (Retrieval-Augmented Generation) module — game strategy knowledge base.

Stores curated guessing-strategy documents and retrieves the most relevant
ones for the current game state using keyword-based scoring.
"""

from __future__ import annotations

# ── Knowledge base ────────────────────────────────────────────────────────────

STRATEGY_DOCS: list[dict] = [
    {
        "id": "binary_search_basic",
        "tags": {"optimal", "strategy", "beginner", "efficient", "start", "first"},
        "content": (
            "Binary search is the mathematically optimal strategy. "
            "Always guess the midpoint of the remaining possible range. "
            "Example: range 1–100, guess 50 first. If Too Low, guess 75 next "
            "(midpoint of 51–100). This halves the search space every guess."
        ),
    },
    {
        "id": "binary_search_math",
        "tags": {"optimal", "advanced", "math", "score", "win fast"},
        "content": (
            "With binary search you need at most ⌈log₂(N)⌉ guesses for a range of N numbers. "
            "Range 1–20 (Easy): 5 guesses max. "
            "Range 1–100 (Normal): 7 guesses max. "
            "Range 1–200 (Hard): 8 guesses max. "
            "Track your current low/high bounds and always guess (low+high)//2."
        ),
    },
    {
        "id": "clustering_too_high",
        "tags": {"too high", "adjust", "correction", "overshooting"},
        "content": (
            "Multiple 'Too High' hints mean you are consistently overshooting. "
            "Don't subtract a small amount — jump much further down. "
            "If your last guess was 80 and the high boundary is 79, "
            "use the midpoint of (current_low, 79) as your next guess."
        ),
    },
    {
        "id": "clustering_too_low",
        "tags": {"too low", "adjust", "correction", "undershooting"},
        "content": (
            "Multiple 'Too Low' hints mean you are consistently undershooting. "
            "Don't add a small amount — jump much further up. "
            "Use the midpoint between your current guess and the high boundary."
        ),
    },
    {
        "id": "few_attempts_left",
        "tags": {"desperate", "few attempts", "last chance", "urgent"},
        "content": (
            "With only 1–2 attempts remaining, commit fully to binary search. "
            "Guess the exact midpoint of the remaining range. "
            "If only 1–3 numbers remain, try the middle one; "
            "avoid the endpoints unless forced."
        ),
    },
    {
        "id": "range_tracking",
        "tags": {"tracking", "range", "boundaries", "mental model"},
        "content": (
            "Always maintain explicit low/high boundaries. "
            "Start: low=range_low, high=range_high. "
            "After 'Too High': high = guess − 1. "
            "After 'Too Low':  low  = guess + 1. "
            "Next guess should always be (low + high) // 2."
        ),
    },
    {
        "id": "scoring_strategy",
        "tags": {"score", "points", "maximize", "win fast"},
        "content": (
            "Scoring rewards fast wins: points = 100 − 10 × (attempts + 1). "
            "To maximise score, win in as few guesses as possible. "
            "Optimal binary search on Normal mode gives a minimum of 20 points "
            "even in the worst case (7 guesses)."
        ),
    },
    {
        "id": "first_guess_tip",
        "tags": {"start", "first", "initial", "opening"},
        "content": (
            "Your very first guess should be the exact midpoint of the full range. "
            "Easy (1–20): guess 10. "
            "Normal (1–100): guess 50. "
            "Hard (1–200): guess 100. "
            "This guarantees the fastest possible convergence."
        ),
    },
]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_strategies(game_state: dict, top_k: int = 3) -> list[dict]:
    """
    Retrieve the top_k most relevant strategy documents for the current state.

    Scores each document by counting how many of its tags appear in the
    keyword set extracted from game_state. Ties are broken by document order.

    Args:
        game_state: dict with keys range_low, range_high, attempts,
                    attempt_limit, history (list of {guess, hint} dicts).
        top_k:      number of documents to return (default 3).

    Returns:
        List of up to top_k strategy dicts (always non-empty).
    """
    keywords = _extract_keywords(game_state)
    scored = sorted(
        STRATEGY_DOCS,
        key=lambda doc: len(doc["tags"] & keywords),
        reverse=True,
    )
    return scored[:top_k]


def _extract_keywords(game_state: dict) -> set[str]:
    """Derive query keywords from the current game state."""
    keywords: set[str] = set()
    attempts      = game_state.get("attempts", 0)
    attempt_limit = game_state.get("attempt_limit", 8)
    hints         = [h.get("hint", "") for h in game_state.get("history", [])]

    # First guess
    if attempts == 0:
        keywords.update({"start", "first", "initial", "opening"})

    # Few attempts remaining
    remaining = attempt_limit - attempts
    if remaining <= 2:
        keywords.update({"desperate", "few attempts", "last chance", "urgent"})

    # Consecutive same hint pattern
    if len(hints) >= 2:
        if hints[-1] == hints[-2] == "Too High":
            keywords.update({"too high", "adjust", "correction", "overshooting"})
        elif hints[-1] == hints[-2] == "Too Low":
            keywords.update({"too low", "adjust", "correction", "undershooting"})
    elif hints:
        if hints[-1] == "Too High":
            keywords.add("too high")
        elif hints[-1] == "Too Low":
            keywords.add("too low")

    # Always useful
    keywords.update({"optimal", "strategy", "tracking", "range", "score"})
    return keywords
