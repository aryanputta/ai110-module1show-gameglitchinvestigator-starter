# 🔐 The Vault — AI-Assisted Number Cracking Game

> **Final Project · AI 110**
> Extended from **Module 1: Game Glitch Investigator**

---

## 🎯 Original Project

**Base project:** Module 1 — Game Glitch Investigator
([aryanputta/ai110-module1show-gameglitchinvestigator-starter](https://github.com/aryanputta/ai110-module1show-gameglitchinvestigator-starter))

The original project was a deliberately broken Streamlit number-guessing game. Students had to find and fix four bugs: a Streamlit session-state bug that regenerated the secret number on every click, backwards Higher/Lower hint logic, a string/int type-flip that corrupted numeric comparisons on even-numbered attempts, and a range-configuration bug where "Hard" mode was actually easier than "Normal". After fixing all four bugs, the game was playable but had no AI features.

---

## ✨ What's New in This Version

| New Feature | File | Description |
|---|---|---|
| **AI Partner (agentic)** | `ai_coach.py` | Claude runs a 3-step tool-use loop before giving advice |
| **RAG knowledge base** | `rag_strategies.py` | 8 strategy documents retrieved by keyword matching |
| **Reliability evaluator** | `evaluator.py` | 6 automated test scenarios with pass/fail report |
| **Vault-cracking UI** | `app.py` | Dark theme, stat cards, guess pills, efficiency meter |
| **Extended test suite** | `tests/test_ai_coach.py` | 23 new unit tests (26 total, all passing) |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER (browser)                             │
│              enters guess · clicks Ask AI Partner               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   app.py  (Streamlit UI)                         │
│  ┌─────────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  Guess input &  │   │  Stat cards  │   │  Guess history   │  │
│  │  Submit button  │   │  (score,     │   │  colour pills    │  │
│  │                 │   │  streak,     │   │  (hot/warm/cold) │  │
│  │  logic_utils.py │   │  efficiency) │   │                  │  │
│  └────────┬────────┘   └──────────────┘   └──────────────────┘  │
│           │                                                       │
│           │ on "Ask AI Partner"                                   │
│           ▼                                                       │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                 ai_coach.py  (GameCoach)                  │   │
│  │                                                           │   │
│  │  ① Claude receives game state + system prompt            │   │
│  │                                                           │   │
│  │  ② Agentic tool-use loop (up to 8 rounds):               │   │
│  │    ┌─────────────────────────────────────────────┐       │   │
│  │    │ Tool A: compute_search_space                │       │   │
│  │    │   → narrows [low,high] from history         │       │   │
│  │    │   → returns optimal next guess (midpoint)   │       │   │
│  │    ├─────────────────────────────────────────────┤       │   │
│  │    │ Tool B: get_strategy_tip  (RAG)             │       │   │
│  │    │   → rag_strategies.py keyword retrieval     │       │   │
│  │    │   → returns top-2 strategy documents        │       │   │
│  │    ├─────────────────────────────────────────────┤       │   │
│  │    │ Tool C: score_player_strategy               │       │   │
│  │    │   → measures deviation from binary search   │       │   │
│  │    │   → returns efficiency score 0–100          │       │   │
│  │    └─────────────────────────────────────────────┘       │   │
│  │                                                           │   │
│  │  ③ Claude synthesises → {advice, confidence 0–1}        │   │
│  └─────────────────┬─────────────────────────────────────────┘   │
│                    │ advice + optimal_next + efficiency_score     │
│                    ▼                                              │
│  ┌─────────────────────────────────┐                             │
│  │  AI Partner panel (right col)   │                             │
│  │  • advice text                  │                             │
│  │  • confidence badge             │                             │
│  │  • "Reveal optimal guess" expander                            │
│  │  • strategy efficiency bar      │                             │
│  └─────────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  evaluator.py  (offline CLI)                     │
│  CoachEvaluator runs 6 test scenarios → prints pass/fail report  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    tests/  (pytest)                              │
│  test_game_logic.py (3)  +  test_ai_coach.py (23) = 26 tests    │
└─────────────────────────────────────────────────────────────────┘
```

**Data flow summary:**
`User guess` → `logic_utils.check_guess()` → `outcome + history` → `GameCoach.get_advice()` → Claude tool loop → `advice + optimal_next + efficiency` → Streamlit UI

---

## 🎮 Game Features

- **Vault-cracking theme** — dark cyber aesthetic, stat cards, colour-coded guess history
- **Three difficulty levels** — Easy (1–20, 6 attempts), Normal (1–100, 8 attempts), Hard (1–200, 5 attempts)
- **Session stats** — vaults cracked, win streak, personal best streak, total score
- **AI Partner** — Claude analyses your guess pattern and tells you what to do next
- **Strategy efficiency meter** — live 0–100% score measuring how close you are to optimal binary search
- **Colour-coded history pills** — 🔴 hot (within 10%), 🟢 warm (within 30%), 🔵 cold (far away)

---

## ⚙️ Setup

### 1 · Install dependencies

```bash
pip install -r requirements.txt
```

### 2 · Set your Anthropic API key (for AI Partner)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

> The game runs without an API key — AI Partner will show a tip about binary search instead.

### 3 · Run the game

```bash
python3 -m streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

### 4 · Run tests

```bash
python3 -m pytest tests/ -v
```

Expected output: **26 passed**

### 5 · Run the reliability evaluator (requires API key)

```bash
python3 evaluator.py
```

---

## 💬 Sample Interactions

### Example 1 — First guess, AI gives opening advice

**Input:** Player opens a Normal game (1–100), clicks "Ask AI Partner" before guessing.

**AI Partner output:**
```
AI Intel 🟢 92% confidence
Your first guess should be 50 — the exact midpoint of the full range.
This halves the search space immediately and gives you the fastest path to the answer.

Optimal next guess: 50
Strategy efficiency: 100%
```

---

### Example 2 — Mid-game binary search in action

**Input:** Player has guessed 50 (Too Low) → 75 (Too High) → 62 (Too Low). Clicks "Ask AI Partner".

**AI Partner output:**
```
AI Intel 🟢 88% confidence
Your remaining range is 63–74 (12 numbers). Guess 68 next — the midpoint.
You're playing near-perfect binary search!

Optimal next guess: 68
Strategy efficiency: 85%  👍 Good — minor deviations.
```

---

### Example 3 — Player is consistently guessing too high

**Input:** Guesses so far: 90 (Too High), 85 (Too High), 80 (Too High).

**AI Partner output:**
```
AI Intel 🟡 75% confidence
You're repeatedly overshooting. Don't subtract a small amount each time —
jump much further down. Your remaining range is 1–79; try 40 as your next guess.

Optimal next guess: 40
Strategy efficiency: 32%  💡 Tip: always guess halfway between your known bounds.
```

---

### Example 4 — Reliability evaluator output

```
python3 evaluator.py

Initialising AI Game Coach …
Running 6 reliability tests — this will take ~30 seconds …

============================================================
  Reliability Report: 6/6 tests passed (100%)
============================================================
  [PASS ✓] empty_state_valid_output
           advice='Your first guess should be 50...' | confidence=0.9
  [PASS ✓] midgame_advice_relevance
           advice='Guess 68 — midpoint of your remaining range...'
  [PASS ✓] optimal_guess_accuracy
           optimal_next=68 (expected 63–74)
  [PASS ✓] confidence_always_in_range
           confidence values: [0.9, 0.88, 0.85]
  [PASS ✓] desperate_state_safety
           advice='With one attempt left, guess 85...' | optimal_next=85
  [PASS ✓] easy_mode_optimal_guess
           optimal_next=5 (expected 1–9)
------------------------------------------------------------
  Average confidence score: 0.87
============================================================
```

---

## 🧠 AI Feature: Agentic Workflow

The AI Partner uses a **multi-step agentic loop** rather than a single prompt-and-response. When you click "Ask AI Partner":

1. **Claude receives** the full game state (range, attempts, guess history)
2. **Claude calls `compute_search_space`** — a pure-Python function that narrows the remaining possible range and computes the optimal binary-search midpoint
3. **Claude calls `get_strategy_tip`** — RAG retrieval from an 8-document knowledge base, returning the 2 most relevant strategy tips based on your game situation
4. **Claude calls `score_player_strategy`** — measures how much each guess deviated from the binary-search optimal, returning a 0–100 efficiency score
5. **Claude synthesises** all three tool results into a 1–2 sentence coaching tip + a confidence score

This means Claude's advice is grounded in mathematical facts about your specific game state, not just generic suggestions. The intermediate tool steps are logged in `coach.log`.

**RAG retrieval** uses keyword matching: game-state signals (first guess? consecutive too-high hints? 1 attempt left?) are mapped to keyword sets, and each strategy document is scored by how many of its tags match. The top 2 documents are passed to Claude as context.

---

## 🛡️ Reliability & Guardrails

| Mechanism | Where | What it does |
|---|---|---|
| Input validation | `logic_utils.parse_guess()` | Rejects non-numeric, empty, and out-of-range inputs |
| Confidence scoring | `ai_coach.py` | Claude outputs confidence 0.0–1.0; always clamped to valid range |
| API key check | `ai_coach.py` | Raises clear `ValueError` if `ANTHROPIC_API_KEY` not set |
| Graceful fallback | `app.py` | Without API key, shows a binary-search tip instead of crashing |
| Agent loop cap | `ai_coach.py` | Maximum 8 tool-use rounds prevents infinite loops |
| Tool error handling | `ai_coach.py` | Every tool call is wrapped in try/except; errors returned as JSON |
| Full logging | `coach.log` | Every tool call, result, and final response is logged |
| Automated tests | `tests/` | 26 tests including edge cases (empty history, 1 attempt left, Easy mode) |
| Evaluator script | `evaluator.py` | 6 scenario tests with pass/fail report — run before demo |

### Test results

```
$ python3 -m pytest tests/ -v
26 passed in 1.10s
```

All 26 tests pass including:
- 7 tests for `compute_search_space` (range narrowing, edge cases)
- 6 tests for `score_player_strategy` (optimal play, poor play, Win hint handling)
- 6 tests for RAG `retrieve_strategies` (correct count, relevance, situation matching)
- 4 tests for keyword extraction
- 3 original game logic tests

---

## 🔧 Design Decisions

**Why Streamlit?** The original project used Streamlit. Keeping the same framework lets evaluators see a clear before/after without a framework switch obscuring the AI additions.

**Why Claude Haiku for the coach?** Haiku is fast (responses in ~3 seconds) and cheap enough for a demo project. The system is model-agnostic — change the `model=` parameter in `GameCoach()` to use any Claude model.

**Why keyword-matching RAG instead of embeddings?** The knowledge base has only 8 documents and the game state produces clear categorical signals (first guess / consecutive hints / desperate). Keyword matching is deterministic, requires no external embedding model, and is fully testable. Embeddings would add latency and an extra dependency for marginal gain.

**Why are tool implementations pure Python?** All three tools (`compute_search_space`, `score_player_strategy`, `get_strategy_tip`) are deterministic Python functions. Keeping them in Python means they can be unit-tested without API calls, their outputs are exact, and they run in milliseconds. Claude's job is synthesis and natural-language output, not arithmetic.

**Trade-offs made:**
- No persistent leaderboard (session-only) — avoids a database dependency
- No streaming responses — simpler code, Streamlit's `st.spinner` handles perceived latency
- RAG is in-memory — fast but non-updatable without code changes

---

## 📊 Reflection & Ethics

### AI limitations and biases
The system's advice is only as good as the strategy knowledge base. It currently only knows binary-search strategies, so it may give suboptimal advice for games where psychological cues (e.g., human-chosen numbers cluster near round numbers) might outperform pure math. The confidence score is self-reported by Claude and is not calibrated against ground truth — it should be treated as a rough signal, not a guarantee.

### Potential misuse
The AI Partner could be misused as a pure cheat engine (always reveal the optimal guess). This is mitigated by the "Reveal optimal guess" expander being opt-in — players can choose to think for themselves and only check after forming their own guess.

### What surprised me about reliability testing
The efficiency scorer initially gave 0 for a "Win" guess because the Win hint was not handled as a loop-break condition. The fix was a single `if hint == "Win": break` line, but catching it required the automated test `test_win_hint_stops_scoring`. Without the test suite, this edge case would have silently produced misleading efficiency scores.

### AI collaboration notes

**Helpful suggestion:** Claude Code correctly identified that `_run_compute_search_space` needed to handle the Win hint by not modifying the range bounds — the explanation was precise and the fix was immediately correct.

**Flawed suggestion:** An early draft of the tool schemas used `oneOf` for the hint enum in the `history` array items, which caused schema validation errors with the Anthropic API. Claude initially insisted the schema was correct and suggested the issue was elsewhere. The actual fix was switching to `"enum": ["Too High", "Too Low", "Win"]` directly on the `hint` property.

---

## 📁 File Structure

```
.
├── app.py                  # Main Streamlit game (extended UI + AI integration)
├── logic_utils.py          # Core game logic (from Module 1, bugs fixed)
├── ai_coach.py             # AI Game Coach — agentic Claude workflow
├── rag_strategies.py       # RAG knowledge base + retrieval
├── evaluator.py            # Reliability test harness (CLI)
├── requirements.txt        # anthropic, streamlit, pytest
├── coach.log               # Auto-generated: AI tool-call log
├── reflection.md           # Module 1 reflection (original)
├── index.html              # Module 1 retro HTML game (original)
├── images/                 # Screenshots
└── tests/
    ├── test_game_logic.py  # Original 3 tests
    └── test_ai_coach.py    # 23 new unit tests
```

---

## 🎥 Video Walkthrough

> Record a Loom video showing:
> - End-to-end game run (2–3 inputs)
> - "Ask AI Partner" button triggering the agentic workflow
> - Evaluator script output in the terminal
> - Win/loss state with score

Add your Loom link here: `https://www.loom.com/share/...`

---

## 🚀 Running Everything

```bash
# 1. Install
pip install -r requirements.txt

# 2. Play the game
export ANTHROPIC_API_KEY=sk-ant-...
python3 -m streamlit run app.py

# 3. Run unit tests
python3 -m pytest tests/ -v

# 4. Run reliability evaluator
python3 evaluator.py
```

---

*Built by extending the Module 1 Game Glitch Investigator · AI Partner powered by Claude (Anthropic API)*
