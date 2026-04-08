"""
Unit tests for ai_coach.py and rag_strategies.py.

Tests cover the pure-Python tool implementations and the RAG retrieval layer —
no live API calls needed.  Run with:

    pytest tests/test_ai_coach.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from ai_coach import (
    _run_compute_search_space,
    _run_score_player_strategy,
)
from rag_strategies import retrieve_strategies, _extract_keywords


# ─────────────────────────────────────────────────────────────────────────────
#  compute_search_space
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeSearchSpace:
    def test_no_history_returns_full_range(self):
        r = _run_compute_search_space(1, 100, [])
        assert r["remaining_low"]  == 1
        assert r["remaining_high"] == 100
        assert r["numbers_remaining"] == 100
        assert r["optimal_next_guess"] == 50

    def test_too_high_narrows_high_bound(self):
        r = _run_compute_search_space(1, 100, [{"guess": 75, "hint": "Too High"}])
        assert r["remaining_high"] == 74

    def test_too_low_narrows_low_bound(self):
        r = _run_compute_search_space(1, 100, [{"guess": 25, "hint": "Too Low"}])
        assert r["remaining_low"] == 26

    def test_binary_search_converges(self):
        # Guesses 50(low), 75(high), 62(low) → range 63–74
        history = [
            {"guess": 50, "hint": "Too Low"},
            {"guess": 75, "hint": "Too High"},
            {"guess": 62, "hint": "Too Low"},
        ]
        r = _run_compute_search_space(1, 100, history)
        assert r["remaining_low"]  == 63
        assert r["remaining_high"] == 74
        assert r["optimal_next_guess"] == 68

    def test_single_number_remaining(self):
        history = [
            {"guess": 50, "hint": "Too Low"},
            {"guess": 52, "hint": "Too High"},
        ]
        r = _run_compute_search_space(1, 100, history)
        assert r["remaining_low"]  == 51
        assert r["remaining_high"] == 51
        assert r["numbers_remaining"] == 1
        assert r["optimal_next_guess"] == 51

    def test_win_hint_does_not_affect_bounds(self):
        history = [{"guess": 42, "hint": "Win"}]
        r = _run_compute_search_space(1, 100, history)
        # Win hint should not change bounds
        assert r["remaining_low"]  == 1
        assert r["remaining_high"] == 100

    def test_easy_mode_range(self):
        r = _run_compute_search_space(1, 20, [{"guess": 10, "hint": "Too High"}])
        assert r["remaining_high"] == 9
        assert r["optimal_next_guess"] == 5


# ─────────────────────────────────────────────────────────────────────────────
#  score_player_strategy
# ─────────────────────────────────────────────────────────────────────────────

class TestScorePlayerStrategy:
    def test_perfect_binary_search_scores_high(self):
        # Optimal guesses for 1–100: 50, then either direction
        result = _run_score_player_strategy(
            range_low=1, range_high=100,
            guesses=[50],
            hints=["Too Low"],
        )
        assert result["score"] == 100

    def test_empty_guesses_returns_100(self):
        result = _run_score_player_strategy(1, 100, [], [])
        assert result["score"] == 100

    def test_poor_strategy_scores_low(self):
        # Guessing 1, 2, 3, 4 … is terrible for range 1–100
        guesses = [1, 2, 3, 4, 5]
        hints   = ["Too Low"] * 5
        result  = _run_score_player_strategy(1, 100, guesses, hints)
        assert result["score"] < 60

    def test_score_in_valid_range(self):
        result = _run_score_player_strategy(
            1, 100, [50, 75, 62], ["Too Low", "Too High", "Too Low"]
        )
        assert 0 <= result["score"] <= 100

    def test_explanation_present(self):
        result = _run_score_player_strategy(1, 100, [50], ["Too Low"])
        assert "explanation" in result
        assert len(result["explanation"]) > 5

    def test_win_hint_stops_scoring(self):
        # After a Win hint, further guesses shouldn't affect score
        result = _run_score_player_strategy(
            1, 100, [50, 99], ["Win", "Too High"]
        )
        # Score should reflect only the first guess
        assert result["score"] == 100


# ─────────────────────────────────────────────────────────────────────────────
#  RAG retrieval
# ─────────────────────────────────────────────────────────────────────────────

class TestRetrieveStrategies:
    def _base_state(self, **kwargs):
        base = {
            "range_low": 1, "range_high": 100,
            "attempts": 0, "attempt_limit": 8,
            "history": [], "difficulty": "Normal",
        }
        base.update(kwargs)
        return base

    def test_returns_correct_count(self):
        docs = retrieve_strategies(self._base_state(), top_k=3)
        assert len(docs) == 3

    def test_top_k_respected(self):
        docs = retrieve_strategies(self._base_state(), top_k=2)
        assert len(docs) == 2

    def test_first_guess_retrieves_opening_doc(self):
        state = self._base_state(attempts=0)
        docs  = retrieve_strategies(state, top_k=5)
        ids   = [d["id"] for d in docs]
        assert "first_guess_tip" in ids or "binary_search_basic" in ids

    def test_too_high_pattern_retrieves_correction_doc(self):
        state = self._base_state(
            attempts=2,
            history=[
                {"guess": 80, "hint": "Too High"},
                {"guess": 70, "hint": "Too High"},
            ],
        )
        docs = retrieve_strategies(state, top_k=5)
        ids  = [d["id"] for d in docs]
        assert "clustering_too_high" in ids

    def test_desperate_state_retrieves_last_chance_doc(self):
        state = self._base_state(
            attempts=7,
            attempt_limit=8,
            history=[{"guess": g, "hint": "Too Low"} for g in [10, 20, 30, 40, 50, 60, 70]],
        )
        docs = retrieve_strategies(state, top_k=5)
        ids  = [d["id"] for d in docs]
        assert "few_attempts_left" in ids

    def test_always_returns_content(self):
        docs = retrieve_strategies(self._base_state())
        for doc in docs:
            assert "content" in doc
            assert len(doc["content"]) > 20


# ─────────────────────────────────────────────────────────────────────────────
#  Keyword extraction
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractKeywords:
    def test_first_attempt_includes_opening_keywords(self):
        state = {"attempts": 0, "attempt_limit": 8, "history": []}
        kw    = _extract_keywords(state)
        assert "start" in kw
        assert "first" in kw

    def test_desperate_includes_urgent_keywords(self):
        state = {"attempts": 7, "attempt_limit": 8, "history": []}
        kw    = _extract_keywords(state)
        assert "desperate" in kw

    def test_consecutive_too_high_hints(self):
        state = {
            "attempts": 2, "attempt_limit": 8,
            "history": [
                {"guess": 80, "hint": "Too High"},
                {"guess": 70, "hint": "Too High"},
            ],
        }
        kw = _extract_keywords(state)
        assert "too high" in kw
        assert "correction" in kw

    def test_always_contains_base_keywords(self):
        kw = _extract_keywords({"attempts": 3, "attempt_limit": 8, "history": []})
        assert "optimal" in kw
        assert "strategy" in kw
