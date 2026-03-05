# 🎮 Game Glitch Investigator: The Impossible Guesser

## 🚨 The Situation

You asked an AI to build a simple "Number Guessing Game" using Streamlit.
It wrote the code, ran away, and now the game is unplayable.

- You can't win.
- The hints lie to you.
- The secret number seems to have commitment issues.

---

## 📖 Game Description

This is a number guessing game where the player tries to guess a randomly chosen secret number within a limited number of attempts. The game gives "Too High" or "Too Low" hints after each incorrect guess to guide the player toward the answer. A score system rewards faster wins. The original AI-generated code shipped with several logic bugs that made the game unwinnable — this project is about finding and fixing them.

---

## 🛠️ Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the fixed Streamlit app: `python -m streamlit run app.py`
3. *(Challenge 4)* Open `index.html` in your browser (or use VS Code Live Server) to play the retro HTML version.

---

## 🕵️‍♂️ Bugs Found & Fixed

### Bug 1 — Secret number kept changing (State Bug)
**What was broken:** Every time the player clicked "Submit", the entire Streamlit script re-ran from the top, generating a new random secret number. The player could never win because the target kept moving.

**Fix applied:** Wrapped the secret number in `st.session_state` so it is generated only once per game and persists across reruns:
```python
if "secret" not in st.session_state:
    st.session_state.secret = random.randint(low, high)
```

### Bug 2 — Higher/Lower hints were backwards (Logic Bug)
**What was broken:** The original `check_guess()` function returned `"Too High"` when the guess was *below* the secret and `"Too Low"` when it was *above* — completely misleading the player.

**Fix applied:** Corrected the comparison in `logic_utils.py`:
```python
if guess > secret:
    return "Too High"
return "Too Low"
```

### Bug 3 — Type-flip on even attempts (Logic Bug)
**What was broken:** On even-numbered attempts, the secret number was silently cast to a string. String comparisons (`"9" > "50"`) are lexicographic, not numeric, so hints became wrong on every other guess.

**Fix applied:** Removed the string cast entirely; the secret stays an `int` throughout.

### Bug 4 — Hard mode was easier than Normal (Range Bug)
**What was broken:** The Hard difficulty used the range `(1, 50)`, which is a *smaller* range than Normal `(1, 100)`, making Hard actually easier.

**Fix noted:** Documented in code comments (`FIXME`). The range for Hard should be larger (e.g., `1, 200`) to truly increase difficulty.

---

## 🔬 Testing

Run the test suite with:
```bash
pytest
```

The tests in `tests/test_game_logic.py` verify:
- A matching guess returns `"Win"`
- A guess above the secret returns `"Too High"`
- A guess below the secret returns `"Too Low"`

All three tests pass after the logic fixes.

---

## 📝 Document Your Experience

- [x] Game purpose: A number guessing game where the player narrows down a hidden number using Higher/Lower hints.
- [x] Bugs found: State bug (secret reset on every rerun), inverted hints, type-flip on even attempts, Hard range smaller than Normal.
- [x] Fixes applied: `st.session_state` for persistence, corrected comparison logic in `logic_utils.py`, removed string cast.

---

## 📸 Demo

### Fixed Streamlit App (Challenges 1–3)

> Screenshot showing the working Streamlit game with correct hints and a winning state.

![Fixed game - winning state](images/gameplay.png)

---

## 🚀 Stretch Feature — Challenge 4: Retro Pixel UI

The enhanced version is a standalone **HTML + CSS + JavaScript** game with a retro arcade aesthetic inspired by classic 8-bit memory card games.

### Features added

| Feature | Description |
|---|---|
| Retro pixel font | Uses *Press Start 2P* (Google Fonts) for a genuine 8-bit look |
| Mystery card | A yellow card with `?` flips and reveals the secret number on a correct guess |
| CRT scanline overlay | A subtle repeating-gradient overlay gives a retro monitor feel |
| HUD bar | Live display of current range, attempt count, and personal best (min attempts) |
| Difficulty selector | Easy (0–20), Normal (0–100), Hard (0–200) — switchable mid-session |
| Shake animation | Input field shakes on a wrong guess for tactile feedback |
| Win overlay | A pop-up overlay announces the win with attempt count |
| Keyboard support | Press **Enter** to submit a guess without touching the mouse |
| Gradient background | Cyan → blue → purple gradient for a retro-futuristic vibe |

### How to run

```bash
# Option 1: VS Code Live Server extension
# Right-click index.html → Open with Live Server

# Option 2: Python simple server
python -m http.server 5500
# then open http://127.0.0.1:5500/index.html
```

### Enhanced UI Screenshots

![Retro game - correct guess](images/retro-correct.png)

![Retro game - gameplay](images/retro-gameplay.png)

---

## 💭 Reflection

See [`reflection.md`](reflection.md) for the full write-up on the debugging process, AI usage, and lessons learned.

---

*Built by an AI that claims this code is production-ready.*
