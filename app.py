"""
The Vault — AI-Assisted Number Cracking Game
============================================
Extended from Module 1 "Game Glitch Investigator" guessing game.

New in this version:
  • Vault-cracking narrative and themed UI
  • AI Partner powered by Claude (agentic tool-use loop)
  • Real-time strategy efficiency meter
  • Streak & personal-best tracking (session)
  • Colour-coded guess history (hot/cold)
  • Optional "reveal optimal hint" from AI Partner
"""

from __future__ import annotations

import os
import random

import streamlit as st

from logic_utils import check_guess, get_range_for_difficulty, parse_guess, update_score

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="The Vault",
    page_icon="🔐",
    layout="wide",
)

# ── Custom CSS — dark vault theme ─────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* ── Base ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0d1117;
        color: #e6edf3;
    }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* ── Title gradient ── */
    .vault-title {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #58a6ff, #79c0ff, #ffa657);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .vault-sub {
        color: #8b949e;
        font-size: 0.95rem;
        margin-top: 2px;
    }

    /* ── Guess history pills ── */
    .guess-pill {
        display: inline-block;
        border-radius: 20px;
        padding: 4px 14px;
        margin: 3px;
        font-weight: 600;
        font-size: 0.88rem;
    }
    .hot  { background-color: #3d1f00; color: #ffa657; border: 1px solid #ffa657; }
    .warm { background-color: #1f2d00; color: #7ee787; border: 1px solid #7ee787; }
    .cold { background-color: #001433; color: #79c0ff; border: 1px solid #79c0ff; }

    /* ── Stat cards ── */
    .stat-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 14px 18px;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 800;
        color: #58a6ff;
    }
    .stat-label {
        font-size: 0.78rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Progress bar override ── */
    .stProgress > div > div > div {
        background-color: #238636 !important;
    }

    /* ── Input ── */
    input[type="text"], input[type="number"] {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px;
    }

    /* ── AI coach box ── */
    .coach-box {
        background: #0d2136;
        border: 1px solid #1f6feb;
        border-left: 4px solid #58a6ff;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 10px;
    }
    .coach-label {
        font-size: 0.75rem;
        color: #58a6ff;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        margin-bottom: 6px;
    }

    /* ── Efficiency bar label ── */
    .eff-label {
        font-size: 0.78rem;
        color: #8b949e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Difficulty config ─────────────────────────────────────────────────────────

DIFFICULTIES = {
    "Easy":   {"limit": 6,  "emoji": "🟢"},
    "Normal": {"limit": 8,  "emoji": "🟡"},
    "Hard":   {"limit": 5,  "emoji": "🔴"},
}

OUTCOME_MSGS = {
    "Win":      "🔓 Vault cracked!",
    "Too High": "📉 Too high — go lower",
    "Too Low":  "📈 Too low — go higher",
}

# ── Session state defaults ────────────────────────────────────────────────────

def _init_session():
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = "Normal"
    diff = st.session_state.difficulty
    low, high = get_range_for_difficulty(diff)

    if "secret" not in st.session_state:
        st.session_state.secret = random.randint(low, high)
    if "attempts" not in st.session_state:
        st.session_state.attempts = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "total_score" not in st.session_state:
        st.session_state.total_score = 0
    if "status" not in st.session_state:
        st.session_state.status = "playing"
    if "history" not in st.session_state:
        st.session_state.history = []       # list of {guess, hint}
    if "streak" not in st.session_state:
        st.session_state.streak = 0
    if "best_streak" not in st.session_state:
        st.session_state.best_streak = 0
    if "vaults_cracked" not in st.session_state:
        st.session_state.vaults_cracked = 0
    if "coach_advice" not in st.session_state:
        st.session_state.coach_advice = None   # last coach response
    if "efficiency" not in st.session_state:
        st.session_state.efficiency = 100


def _start_new_game(difficulty: str):
    """Reset game state for a new vault, preserving cross-game stats."""
    low, high = get_range_for_difficulty(difficulty)
    st.session_state.difficulty = difficulty
    st.session_state.secret     = random.randint(low, high)
    st.session_state.attempts   = 0
    st.session_state.score      = 0
    st.session_state.status     = "playing"
    st.session_state.history    = []
    st.session_state.coach_advice = None
    st.session_state.efficiency   = 100


# ── Helper: colour code a guess ───────────────────────────────────────────────

def _guess_class(guess: int, secret: int, low: int, high: int) -> str:
    """Return CSS class based on how close the guess is (hot/warm/cold)."""
    total_range = high - low or 1
    distance    = abs(guess - secret)
    ratio       = distance / total_range
    if ratio <= 0.1:
        return "hot"
    if ratio <= 0.3:
        return "warm"
    return "cold"


# ── Helper: efficiency score using binary-search deviation ───────────────────

def _compute_efficiency(history: list[dict], range_low: int, range_high: int) -> int:
    """Return 0–100 score reflecting how close guesses were to binary-search midpoints."""
    if not history:
        return 100
    low, high = range_low, range_high
    total_dev = 0.0
    for entry in history:
        guess = entry["guess"]
        hint  = entry["hint"]
        if hint == "Win":
            break
        optimal = (low + high) // 2
        max_dev = max((high - low) // 2, 1)
        total_dev += abs(guess - optimal) / max_dev
        if hint == "Too High":
            high = min(high, guess - 1)
        elif hint == "Too Low":
            low  = max(low, guess + 1)
    n = len(history)
    return max(0, int(100 * (1 - total_dev / n)))


# ── AI Coach helper ───────────────────────────────────────────────────────────

def _get_coach_advice():
    """Call the AI Coach and store the result in session state."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.session_state.coach_advice = {
            "advice": (
                "Set ANTHROPIC_API_KEY to enable AI coaching. "
                "Tip: always guess the midpoint of the remaining range!"
            ),
            "confidence": 0.0,
            "optimal_next": None,
            "efficiency_score": st.session_state.efficiency,
        }
        return

    diff = st.session_state.difficulty
    low, high = get_range_for_difficulty(diff)

    game_state = {
        "range_low":     low,
        "range_high":    high,
        "attempts":      st.session_state.attempts,
        "attempt_limit": DIFFICULTIES[diff]["limit"],
        "history":       st.session_state.history,
        "difficulty":    diff,
    }

    try:
        from ai_coach import GameCoach
        coach  = GameCoach(api_key=api_key)
        result = coach.get_advice(game_state)
        st.session_state.coach_advice = result
    except Exception as exc:
        st.session_state.coach_advice = {
            "advice": f"Coach unavailable: {exc}",
            "confidence": 0.0,
            "optimal_next": None,
            "efficiency_score": st.session_state.efficiency,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

_init_session()

diff  = st.session_state.difficulty
low, high = get_range_for_difficulty(diff)
limit = DIFFICULTIES[diff]["limit"]

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔐 The Vault")
    st.caption("AI-Assisted Number Cracking")
    st.divider()

    new_diff = st.selectbox(
        "Difficulty",
        list(DIFFICULTIES.keys()),
        index=list(DIFFICULTIES.keys()).index(diff),
        format_func=lambda d: f"{DIFFICULTIES[d]['emoji']} {d}",
    )

    if new_diff != diff:
        _start_new_game(new_diff)
        st.rerun()

    st.caption(f"Range: **{low} – {high}**")
    st.caption(f"Attempts: **{limit}**")

    st.divider()

    # Session stats
    st.markdown("#### Session Stats")
    col_a, col_b = st.columns(2)
    col_a.metric("Vaults Cracked", st.session_state.vaults_cracked)
    col_b.metric("Best Streak",    st.session_state.best_streak)
    st.metric("Total Score", st.session_state.total_score)

    st.divider()

    if st.button("🔄 New Vault", use_container_width=True):
        _start_new_game(diff)
        st.rerun()

    with st.expander("🛠 Developer Debug"):
        st.write("Secret:", st.session_state.secret)
        st.write("Status:", st.session_state.status)
        st.write("History:", st.session_state.history)

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown('<p class="vault-title">🔐 The Vault</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="vault-sub">Crack the combination before your attempts run out. '
    'Your AI partner is standing by.</p>',
    unsafe_allow_html=True,
)
st.write("")

# ── Top stats row ─────────────────────────────────────────────────────────────

remaining_attempts = limit - st.session_state.attempts
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="stat-card"><div class="stat-number">{remaining_attempts}</div>'
        f'<div class="stat-label">Attempts Left</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="stat-card"><div class="stat-number">{st.session_state.score}</div>'
        f'<div class="stat-label">Round Score</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="stat-card"><div class="stat-number">{st.session_state.streak}</div>'
        f'<div class="stat-label">Win Streak</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    eff = st.session_state.efficiency
    st.markdown(
        f'<div class="stat-card"><div class="stat-number">{eff}%</div>'
        f'<div class="stat-label">Strategy Score</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Attempts progress bar ─────────────────────────────────────────────────────

bar_pct  = (limit - remaining_attempts) / limit
bar_color = "🟢" if remaining_attempts >= 4 else ("🟡" if remaining_attempts >= 2 else "🔴")
st.caption(f"Attempts used: {st.session_state.attempts}/{limit}  {bar_color}")
st.progress(bar_pct)

st.write("")
main_col, coach_col = st.columns([3, 2])

# ── Main game column ──────────────────────────────────────────────────────────

with main_col:
    st.subheader(f"Enter the vault combination  ({low} – {high})")

    if st.session_state.status != "playing":
        if st.session_state.status == "won":
            st.success(
                f"🏆 Vault cracked!  Secret was **{st.session_state.secret}**.  "
                f"Round score: **{st.session_state.score}**"
            )
            st.balloons()
        else:
            st.error(
                f"💀 Vault locked!  The combination was **{st.session_state.secret}**.  "
                f"Score: **{st.session_state.score}**"
            )
        st.info("Open a new vault from the sidebar to play again.")

    else:
        raw_guess = st.text_input(
            "Your guess:",
            placeholder=f"Enter a number between {low} and {high}",
            key=f"guess_{diff}_{st.session_state.attempts}",
            label_visibility="collapsed",
        )

        b1, b2 = st.columns([1, 1])
        submit    = b1.button("🔓 Submit", use_container_width=True)
        ask_coach = b2.button("🤖 Ask AI Partner", use_container_width=True)

        # ── Ask AI Coach ──────────────────────────────────────────────────────
        if ask_coach:
            with st.spinner("Analysing your strategy …"):
                _get_coach_advice()

        # ── Submit guess ──────────────────────────────────────────────────────
        if submit and raw_guess:
            st.session_state.attempts += 1

            ok, guess_int, err = parse_guess(raw_guess)

            if not ok:
                st.session_state.attempts -= 1   # don't charge for invalid input
                st.error(f"⚠️  {err}")
            else:
                secret  = st.session_state.secret
                outcome = check_guess(guess_int, secret)

                st.session_state.history.append({"guess": guess_int, "hint": outcome})

                st.session_state.score = update_score(
                    current_score=st.session_state.score,
                    outcome=outcome,
                    attempt_number=st.session_state.attempts,
                )

                # Update efficiency
                st.session_state.efficiency = _compute_efficiency(
                    st.session_state.history, low, high
                )

                msg = OUTCOME_MSGS.get(outcome, "")

                if outcome == "Win":
                    st.session_state.status        = "won"
                    st.session_state.streak       += 1
                    st.session_state.vaults_cracked += 1
                    st.session_state.total_score  += st.session_state.score
                    st.session_state.best_streak   = max(
                        st.session_state.streak, st.session_state.best_streak
                    )
                    st.rerun()

                elif st.session_state.attempts >= limit:
                    st.session_state.status       = "lost"
                    st.session_state.streak       = 0
                    st.session_state.total_score += st.session_state.score
                    st.rerun()

                else:
                    if outcome == "Too High":
                        st.warning(msg)
                    else:
                        st.info(msg)

    # ── Guess history ─────────────────────────────────────────────────────────
    if st.session_state.history:
        st.write("")
        st.caption("Guess history")
        pills_html = ""
        for entry in st.session_state.history:
            g    = entry["guess"]
            hint = entry["hint"]
            if hint == "Win":
                css = "hot"
                label = f"✅ {g}"
            elif hint == "Too High":
                css = "cold"
                label = f"↓ {g}"
            else:
                css = "warm"
                label = f"↑ {g}"
            pills_html += f'<span class="guess-pill {css}">{label}</span>'
        st.markdown(pills_html, unsafe_allow_html=True)

# ── AI Coach column ───────────────────────────────────────────────────────────

with coach_col:
    st.subheader("🤖 AI Partner")

    if st.session_state.coach_advice is None:
        st.markdown(
            '<div class="coach-box">'
            '<div class="coach-label">Waiting for signal …</div>'
            "Click <b>Ask AI Partner</b> at any point during the game to get "
            "a strategic recommendation from your AI partner. "
            "The AI analyses your guess history and computes the optimal next move."
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        adv  = st.session_state.coach_advice
        conf = adv.get("confidence", 0.0)
        opt  = adv.get("optimal_next")
        eff  = adv.get("efficiency_score", st.session_state.efficiency)

        # Advice box
        conf_pct = int(conf * 100)
        conf_emoji = "🟢" if conf >= 0.8 else ("🟡" if conf >= 0.5 else "🔴")
        st.markdown(
            f'<div class="coach-box">'
            f'<div class="coach-label">AI Intel  {conf_emoji} {conf_pct}% confidence</div>'
            f'{adv.get("advice", "")}'
            f"</div>",
            unsafe_allow_html=True,
        )

        # Optimal guess
        if opt is not None and st.session_state.status == "playing":
            st.write("")
            with st.expander("💡 Reveal optimal guess"):
                st.info(
                    f"Optimal next guess: **{opt}**  \n"
                    "(This is the binary-search midpoint of the remaining range.)"
                )

        # Efficiency
        st.write("")
        st.caption(f"Strategy efficiency: **{eff}%**")
        st.progress(eff / 100)
        if eff >= 85:
            st.caption("🏆 Excellent — near-optimal binary search!")
        elif eff >= 60:
            st.caption("👍 Good strategy — minor deviations.")
        elif eff >= 40:
            st.caption("⚠️  Try staying closer to the midpoint.")
        else:
            st.caption("💡 Tip: always guess halfway between your known bounds.")

    st.write("")
    st.divider()
    st.caption(
        "The AI Partner uses an **agentic workflow**: it calls three tools "
        "(search-space calculator, strategy knowledge base, efficiency scorer) "
        "before giving you advice."
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.write("")
st.caption(
    "Built by extending the Module 1 Game Glitch Investigator · "
    "AI Partner powered by Claude via the Anthropic API"
)
