"""
AI Game Coach — agentic workflow using Claude with tool use.

The coach runs a 3-step agentic loop before giving advice:
  1. compute_search_space  — narrows the remaining possible range from guess history
  2. get_strategy_tip      — RAG lookup for the most relevant coaching tip
  3. score_player_strategy — rates how close the player is to optimal binary search

Claude decides which tools to call (and in what order), then synthesises
a concise, actionable coaching tip with a confidence score.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from rag_strategies import retrieve_strategies

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("coach.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ai_coach")


# ── Tool schemas (passed to Claude) ──────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "compute_search_space",
        "description": (
            "Given the original game range and the player's guess history "
            "(each entry has a 'guess' integer and a 'hint' string), compute "
            "the remaining possible range [low, high], the count of numbers "
            "still possible, and the mathematically optimal next guess."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "range_low":  {"type": "integer", "description": "Original game low bound (inclusive)"},
                "range_high": {"type": "integer", "description": "Original game high bound (inclusive)"},
                "history": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "guess": {"type": "integer"},
                            "hint":  {"type": "string", "enum": ["Too High", "Too Low", "Win"]},
                        },
                        "required": ["guess", "hint"],
                    },
                    "description": "Ordered list of (guess, hint) pairs so far",
                },
            },
            "required": ["range_low", "range_high", "history"],
        },
    },
    {
        "name": "get_strategy_tip",
        "description": (
            "Retrieve a relevant guessing-strategy tip from the knowledge base "
            "based on a short description of the current game situation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "situation": {
                    "type": "string",
                    "description": (
                        "Brief description of the situation, e.g. "
                        "'player keeps guessing too high' or 'first guess, Normal mode'"
                    ),
                },
            },
            "required": ["situation"],
        },
    },
    {
        "name": "score_player_strategy",
        "description": (
            "Evaluate how close the player's guesses are to the optimal binary-search "
            "strategy. Returns an integer efficiency score 0–100 and a brief explanation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "range_low":  {"type": "integer"},
                "range_high": {"type": "integer"},
                "guesses": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Player's guesses in order",
                },
                "hints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Corresponding hints in order",
                },
            },
            "required": ["range_low", "range_high", "guesses", "hints"],
        },
    },
]


# ── Pure-Python tool implementations ─────────────────────────────────────────

def _run_compute_search_space(
    range_low: int, range_high: int, history: list[dict]
) -> dict:
    """Narrow range using guess/hint pairs; return remaining range + optimal next."""
    low, high = range_low, range_high
    for entry in history:
        hint = entry.get("hint", "")
        g    = entry.get("guess", 0)
        if hint == "Too High":
            high = min(high, g - 1)
        elif hint == "Too Low":
            low = max(low, g + 1)

    remaining = max(0, high - low + 1)
    optimal   = (low + high) // 2 if remaining > 0 else None
    return {
        "remaining_low":     low,
        "remaining_high":    high,
        "numbers_remaining": remaining,
        "optimal_next_guess": optimal,
    }


def _run_get_strategy_tip(situation: str, game_state: dict) -> dict:
    """RAG lookup: return top-2 relevant strategy tips."""
    docs = retrieve_strategies(game_state, top_k=2)
    return {
        "situation": situation,
        "tips": [doc["content"] for doc in docs],
    }


def _run_score_player_strategy(
    range_low: int, range_high: int, guesses: list[int], hints: list[str]
) -> dict:
    """Score how close each guess was to the binary-search midpoint."""
    if not guesses:
        return {"score": 100, "explanation": "No guesses yet — perfect score by default."}

    low, high  = range_low, range_high
    total_dev  = 0.0

    for guess, hint in zip(guesses, hints):
        if hint == "Win":
            break
        optimal   = (low + high) // 2
        max_dev   = max((high - low) // 2, 1)
        total_dev += abs(guess - optimal) / max_dev

        if hint == "Too High":
            high = min(high, guess - 1)
        elif hint == "Too Low":
            low  = max(low, guess + 1)

    n   = len(guesses)
    avg = total_dev / n if n else 0.0
    score = max(0, int(100 * (1 - avg)))

    if score >= 85:
        explanation = "Excellent — nearly optimal binary search!"
    elif score >= 60:
        explanation = "Good — minor deviations from optimal."
    elif score >= 40:
        explanation = "Moderate — try staying closer to the midpoint each time."
    else:
        explanation = "Needs work — try always guessing the midpoint of the remaining range."

    return {"score": score, "explanation": explanation}


def _dispatch_tool(tool_name: str, tool_input: dict, game_state: dict) -> str:
    """Execute a tool by name and return its result as a JSON string."""
    logger.info("Tool call → %s | input: %s", tool_name, tool_input)
    try:
        if tool_name == "compute_search_space":
            result = _run_compute_search_space(**tool_input)
        elif tool_name == "get_strategy_tip":
            result = _run_get_strategy_tip(game_state=game_state, **tool_input)
        elif tool_name == "score_player_strategy":
            result = _run_score_player_strategy(**tool_input)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as exc:
        logger.error("Tool %s raised: %s", tool_name, exc, exc_info=True)
        result = {"error": str(exc)}
    logger.info("Tool result ← %s | %s", tool_name, result)
    return json.dumps(result)


# ── GameCoach ─────────────────────────────────────────────────────────────────

class GameCoach:
    """
    AI coach that analyses a player's game state and gives strategic advice.

    Uses an agentic Claude loop: Claude decides which tools to call, the tools
    run locally, and Claude synthesises the results into a coaching tip.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it as an environment variable or pass api_key= to GameCoach()."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model  = model
        logger.info("GameCoach ready | model=%s", model)

    def get_advice(self, game_state: dict) -> dict:
        """
        Run the agentic workflow and return a coaching response.

        Args:
            game_state: {
                "range_low":     int,
                "range_high":    int,
                "attempts":      int,
                "attempt_limit": int,
                "history":       [{"guess": int, "hint": str}, ...],
                "difficulty":    str,
            }

        Returns:
            {
                "advice":           str,   # 1–2 sentence coaching tip
                "confidence":       float, # 0.0 – 1.0
                "optimal_next":     int | None,
                "efficiency_score": int,   # 0 – 100
            }
        """
        logger.info("get_advice called | %s", game_state)

        system_prompt = (
            "You are a friendly, concise game coach for a number-guessing game. "
            "You have three tools: compute_search_space, get_strategy_tip, and "
            "score_player_strategy. Use all three before giving your final answer. "
            "After using the tools, respond ONLY with a valid JSON object with "
            'exactly these keys: {"advice": "<1–2 sentence tip>", "confidence": <0.0–1.0>}. '
            "No extra text before or after the JSON."
        )

        attempts = game_state.get("attempts", 0)
        limit    = game_state.get("attempt_limit", 8)
        history  = game_state.get("history", [])

        user_message = (
            f"Game state — difficulty: {game_state.get('difficulty', 'Normal')}, "
            f"range: {game_state['range_low']}–{game_state['range_high']}, "
            f"attempts used: {attempts}/{limit}, "
            f"guess history: {history}. "
            "Analyse this and give the player one concise, actionable coaching tip."
        )

        messages: list[dict] = [{"role": "user", "content": user_message}]
        efficiency_score = 50
        optimal_next: int | None = None

        # Agentic loop — allow up to 8 rounds of tool use
        for round_num in range(8):
            logger.info("Agent round %d", round_num)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )
            logger.info("Stop reason: %s", response.stop_reason)

            tool_uses = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason == "end_turn" or not tool_uses:
                # Extract the final JSON response
                text_blocks = [b for b in response.content if b.type == "text"]
                raw = text_blocks[0].text.strip() if text_blocks else "{}"
                logger.info("Final text: %s", raw)

                try:
                    j_start = raw.find("{")
                    j_end   = raw.rfind("}") + 1
                    parsed  = json.loads(raw[j_start:j_end])
                    advice     = str(parsed.get("advice", "Try guessing the midpoint of the remaining range."))
                    confidence = float(parsed.get("confidence", 0.75))
                    confidence = max(0.0, min(1.0, confidence))
                except (json.JSONDecodeError, ValueError, IndexError):
                    advice     = raw[:300] if raw else "Try using binary search — always guess the midpoint."
                    confidence = 0.6

                return {
                    "advice":           advice,
                    "confidence":       confidence,
                    "optimal_next":     optimal_next,
                    "efficiency_score": efficiency_score,
                }

            # Feed tool results back to Claude
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for tu in tool_uses:
                result_str = _dispatch_tool(tu.name, tu.input, game_state)

                # Cache key numbers so we can surface them in the UI
                if tu.name == "compute_search_space":
                    r = json.loads(result_str)
                    optimal_next = r.get("optimal_next_guess")
                elif tu.name == "score_player_strategy":
                    r = json.loads(result_str)
                    efficiency_score = r.get("score", 50)

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tu.id,
                    "content":     result_str,
                })

            messages.append({"role": "user", "content": tool_results})

        # Fallback if agent loop exhausted without a final response
        logger.warning("Agent loop exhausted — returning fallback advice")
        return {
            "advice":           "Use binary search: always guess the midpoint of your remaining range.",
            "confidence":       0.5,
            "optimal_next":     optimal_next,
            "efficiency_score": efficiency_score,
        }
