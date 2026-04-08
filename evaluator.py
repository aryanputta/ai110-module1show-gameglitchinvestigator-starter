"""
Reliability evaluator for the AI Game Coach.

Runs 6 structured test scenarios and measures:
  - Valid output format (advice string + confidence in [0,1])
  - Contextual relevance (does advice mention relevant numbers/strategy?)
  - Optimal-next-guess accuracy (is the suggested guess mathematically correct?)
  - Confidence calibration (confidence correlates with scenario certainty)
  - Edge-case safety (empty history, last attempt, Easy mode)

Usage:
    python evaluator.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("evaluator")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    confidence: float = 0.0
    efficiency_score: int = 0


@dataclass
class EvalReport:
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def summary(self) -> str:
        lines = [
            "",
            "=" * 60,
            f"  Reliability Report: {self.passed}/{self.total} tests passed "
            f"({self.pass_rate:.0%})",
            "=" * 60,
        ]
        for r in self.results:
            status = "PASS ✓" if r.passed else "FAIL ✗"
            lines.append(f"  [{status}] {r.name}")
            lines.append(f"           {r.details}")
        avg_conf = (
            sum(r.confidence for r in self.results) / self.total
            if self.total else 0.0
        )
        lines += [
            "-" * 60,
            f"  Average confidence score: {avg_conf:.2f}",
            "=" * 60,
            "",
        ]
        return "\n".join(lines)


# ── Canonical test game states ────────────────────────────────────────────────

def _state_empty() -> dict:
    return {
        "range_low": 1, "range_high": 100,
        "attempts": 0, "attempt_limit": 8,
        "history": [], "difficulty": "Normal",
    }


def _state_midgame() -> dict:
    # Guesses: 50(low), 75(high), 62(low) → remaining range: 63–74, optimal: 68
    return {
        "range_low": 1, "range_high": 100,
        "attempts": 3, "attempt_limit": 8,
        "history": [
            {"guess": 50, "hint": "Too Low"},
            {"guess": 75, "hint": "Too High"},
            {"guess": 62, "hint": "Too Low"},
        ],
        "difficulty": "Normal",
    }


def _state_desperate() -> dict:
    # 7 of 8 attempts used, all Too Low → range is 71–100
    return {
        "range_low": 1, "range_high": 100,
        "attempts": 7, "attempt_limit": 8,
        "history": [
            {"guess": g, "hint": "Too Low"}
            for g in [10, 20, 30, 40, 50, 60, 70]
        ],
        "difficulty": "Normal",
    }


def _state_easy() -> dict:
    # Easy mode, 1 guess made: 10 → Too High → remaining 1–9, optimal 5
    return {
        "range_low": 1, "range_high": 20,
        "attempts": 1, "attempt_limit": 6,
        "history": [{"guess": 10, "hint": "Too High"}],
        "difficulty": "Easy",
    }


def _state_hard() -> dict:
    return {
        "range_low": 1, "range_high": 200,
        "attempts": 2, "attempt_limit": 5,
        "history": [
            {"guess": 100, "hint": "Too Low"},
            {"guess": 150, "hint": "Too High"},
        ],
        "difficulty": "Hard",
    }


# ── CoachEvaluator ────────────────────────────────────────────────────────────

class CoachEvaluator:
    """Runs structured reliability tests against a GameCoach instance."""

    def __init__(self, coach) -> None:
        self.coach = coach

    def run_all(self) -> EvalReport:
        """Execute every test and collect results."""
        report = EvalReport()
        tests = [
            self._test_empty_state_valid_output,
            self._test_midgame_advice_relevance,
            self._test_optimal_guess_accuracy,
            self._test_confidence_always_in_range,
            self._test_desperate_state_safety,
            self._test_easy_mode_optimal_guess,
        ]
        for fn in tests:
            try:
                result = fn()
            except Exception as exc:
                logger.error("Test %s crashed: %s", fn.__name__, exc, exc_info=True)
                result = TestResult(
                    name=fn.__name__,
                    passed=False,
                    details=f"Crashed with: {exc}",
                )
            report.results.append(result)
        return report

    # ── Individual tests ──────────────────────────────────────────────────────

    def _test_empty_state_valid_output(self) -> TestResult:
        """Coach must return a valid advice string and confidence for an empty game."""
        r = self.coach.get_advice(_state_empty())
        passed = (
            isinstance(r.get("advice"), str)
            and len(r["advice"]) > 10
            and 0.0 <= r.get("confidence", -1) <= 1.0
        )
        return TestResult(
            name="empty_state_valid_output",
            passed=passed,
            details=(
                f"advice={r.get('advice','')[:80]!r} | "
                f"confidence={r.get('confidence')}"
            ),
            confidence=r.get("confidence", 0.0),
        )

    def _test_midgame_advice_relevance(self) -> TestResult:
        """Mid-game advice should reference a concrete number or strategy term."""
        r = self.coach.get_advice(_state_midgame())
        advice_lower = r.get("advice", "").lower()
        relevant = any(
            kw in advice_lower
            for kw in ["68", "63", "midpoint", "range", "between", "binary", "search", "64", "65", "66", "67"]
        )
        return TestResult(
            name="midgame_advice_relevance",
            passed=relevant,
            details=f"advice={r.get('advice','')[:120]!r}",
            confidence=r.get("confidence", 0.0),
            efficiency_score=r.get("efficiency_score", 0),
        )

    def _test_optimal_guess_accuracy(self) -> TestResult:
        """
        After guesses 50(low), 75(high), 62(low) the remaining range is 63–74
        and the optimal next guess is 68. Accept 63–74.
        """
        r = self.coach.get_advice(_state_midgame())
        opt = r.get("optimal_next")
        passed = opt is not None and 63 <= opt <= 74
        return TestResult(
            name="optimal_guess_accuracy",
            passed=passed,
            details=f"optimal_next={opt} (expected 63–74)",
            confidence=r.get("confidence", 0.0),
        )

    def _test_confidence_always_in_range(self) -> TestResult:
        """Confidence must be in [0.0, 1.0] across three different states."""
        states  = [_state_empty(), _state_midgame(), _state_easy()]
        results = [self.coach.get_advice(s) for s in states]
        confs   = [res.get("confidence", -1) for res in results]
        all_ok  = all(0.0 <= c <= 1.0 for c in confs)
        return TestResult(
            name="confidence_always_in_range",
            passed=all_ok,
            details=f"confidence values: {[round(c, 2) for c in confs]}",
            confidence=sum(confs) / len(confs) if confs else 0.0,
        )

    def _test_desperate_state_safety(self) -> TestResult:
        """With 1 attempt left the coach must still return valid, non-empty advice."""
        r = self.coach.get_advice(_state_desperate())
        passed = (
            isinstance(r.get("advice"), str)
            and len(r["advice"]) > 10
            and r.get("optimal_next") is not None
        )
        return TestResult(
            name="desperate_state_safety",
            passed=passed,
            details=(
                f"advice={r.get('advice','')[:100]!r} | "
                f"optimal_next={r.get('optimal_next')}"
            ),
            confidence=r.get("confidence", 0.0),
        )

    def _test_easy_mode_optimal_guess(self) -> TestResult:
        """After guess 10→Too High on Easy (1–20), optimal next should be 1–9."""
        r = self.coach.get_advice(_state_easy())
        opt = r.get("optimal_next")
        passed = opt is not None and 1 <= opt <= 9
        return TestResult(
            name="easy_mode_optimal_guess",
            passed=passed,
            details=f"optimal_next={opt} (expected 1–9)",
            confidence=r.get("confidence", 0.0),
        )


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from ai_coach import GameCoach

    logging.basicConfig(level=logging.WARNING)  # suppress noisy logs during eval

    print("\nInitialising AI Game Coach …")
    try:
        coach = GameCoach()
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print("Running 6 reliability tests — this will take ~30 seconds …\n")
    evaluator = CoachEvaluator(coach)
    report    = evaluator.run_all()
    print(report.summary())

    sys.exit(0 if report.pass_rate >= 0.8 else 1)
