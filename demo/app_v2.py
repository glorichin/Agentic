"""
app.py — Titan MIP · Streamlit Demo
─────────────────────────────────────────────────────────────────
A live demo of the 5-agent Maintenance Intelligence Platform.

Run it:
    pip install -r requirements.txt
    # make sure your key is in .env  (GEMINI_API_KEY=...)
    streamlit run app.py

What it shows:
  • The incoming sensor-breach event (the trigger)
  • Each specialist agent's assessment as it completes, live
  • The Safety & Governance gate decision
  • The Orchestrator's final synthesized decision (autonomous vs escalate)
"""

import streamlit as st

# v2: import the interactive engine — the sidebar Reading value / Threshold now
# flow through to the agents and genuinely change the decision.
from titan_agents_v2 import run_pipeline, DEMO_EVENT, GEMINI_API_KEY, GEMINI_MODEL
# v2: per-asset thresholds so the Threshold box auto-fills for the chosen asset.
from step2_mock_tools_v2 import get_thresholds

# v2: per-signal display defaults + which threshold key each signal maps to.
SIGNAL_META = {
    "spindle_vibration": {"thr_key": "vibration_g", "value": 0.48, "step": 0.01,
                          "unit": "g"},
    "temperature":       {"thr_key": "temp_c",      "value": 92.0, "step": 0.5,
                          "unit": "°C"},
    "motor_current":     {"thr_key": "motor_amp",   "value": 22.4, "step": 0.1,
                          "unit": "A"},
}


# ─────────────────────────────────────────────────────────────────
# Page setup
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Titan MIP — Maintenance Intelligence",
    page_icon="🏭",
    layout="wide",
)

AGENT_META = {
    "reliability": ("📡", "Reliability Intelligence", "Asset health & failure risk"),
    "process":     ("🔍", "Process Intelligence",     "Workflow & bottlenecks"),
    "cost":        ("💰", "Cost Intelligence",         "Financial & business impact"),
    "governance":  ("🛡️", "Safety & Governance",       "Policy & approval gate"),
    "orchestrator":("⚙️", "Orchestrator",              "Synthesis & final decision"),
}

RISK_COLOR = {
    "CRITICAL": "#A32D2D", "HIGH": "#993C1D", "AT_RISK": "#854F0B",
    "MEDIUM": "#854F0B", "WATCH": "#185FA5", "LOW": "#3B6D11", "HEALTHY": "#3B6D11",
}


# ─────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────
st.title("🏭 Titan Maintenance Intelligence Platform")
st.caption(
    "Agentic AI — Challenge 1: Asset Reliability & Predictive Maintenance · "
    "Hierarchical multi-agent crew (CrewAI + Gemini) · IE Business School"
)


# ─────────────────────────────────────────────────────────────────
# Sidebar — scenario controls
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚡ Trigger event")

    asset_id = st.selectbox(
        "Asset",
        ["CNC-Lathe-07", "CNC-Lathe-03", "Robot-Cell-12", "Conveyor-B4"],
        index=0,
        help="CNC-Lathe-07 is the degraded demo asset from the case study.",
    )
    plant = st.text_input("Plant", DEMO_EVENT["plant"])
    signal = st.selectbox(
        "Signal", ["spindle_vibration", "temperature", "motor_current"], index=0
    )

    meta = SIGNAL_META[signal]
    # Threshold auto-fills with THIS asset's safe limit for THIS signal. The key
    # depends on asset+signal so it refreshes when either changes.
    asset_threshold = float(get_thresholds(asset_id)[meta["thr_key"]])

    value = st.number_input(
        f"Reading value ({meta['unit']})",
        value=float(meta["value"]), step=meta["step"], key=f"val_{signal}",
    )
    # Threshold is the asset's FIXED safe limit — shown read-only (no steppers).
    st.text_input(
        "Threshold (fixed safe limit)",
        value=str(asset_threshold), disabled=True,
        key=f"thr_disp_{asset_id}_{signal}",
    )
    threshold = asset_threshold

    st.divider()
    st.markdown("**LLM**")
    st.code(GEMINI_MODEL, language=None)
    if GEMINI_API_KEY:
        st.success(f"API key loaded ({GEMINI_API_KEY[:6]}…)", icon="✅")
    else:
        st.error("No GEMINI_API_KEY in .env", icon="🚫")

    run = st.button("▶  Run the crew", type="primary", use_container_width=True)


# All signals now use the same unit as their threshold (vibration g,
# temperature °C, current A), so it's one simple comparison.
breach = value > threshold

# Option B: only a real breach is a trigger event; otherwise it's a normal read.
event_type = "SENSOR_THRESHOLD_BREACH" if breach else "NORMAL_READING"

event = {
    "event_type": event_type,
    "asset_id": asset_id,
    "plant": plant,
    "signal": signal,
    "value": value,
    "threshold": threshold,
    "timestamp": DEMO_EVENT["timestamp"],
}


# ─────────────────────────────────────────────────────────────────
# Show the trigger event
# ─────────────────────────────────────────────────────────────────
c1, c2 = st.columns([2, 3])
with c1:
    st.subheader("Incoming event")
    st.metric(
        label=f"{signal}  ·  {asset_id}",
        value=f"{value}",
        delta=f"{round((value - threshold) / threshold * 100)}% vs threshold "
              f"{threshold}",
        delta_color="inverse" if breach else "normal",
    )
    if not breach:
        st.caption("✅ Within limits — in production this would **not** trigger "
                   "the crew (shown here for exploration).")
with c2:
    st.subheader("Event details")
    d1, d2 = st.columns(2)
    d1.markdown(f"**Event type**  \n`{event['event_type']}`")
    d2.markdown(f"**Signal**  \n`{event['signal']}`")
    d1.markdown(f"**Plant**  \n{event['plant']}")
    d2.markdown(f"**Timestamp**  \n{event['timestamp']}")
    with st.expander("Full event payload (JSON)"):
        st.json(event, expanded=True)


# ─────────────────────────────────────────────────────────────────
# Helpers to render each agent's card
# ─────────────────────────────────────────────────────────────────
def _fmt_money(v):
    try:
        return f"${int(round(float(v))):,}"
    except Exception:
        return str(v)


def _fmt_bool(v):
    if isinstance(v, bool):
        return "Yes" if v else "No"
    s = str(v).strip().lower()
    if s in ("true", "yes"):
        return "Yes"
    if s in ("false", "no"):
        return "No"
    return str(v)


def _count(v):
    return len(v) if isinstance(v, list) else v


def _fmt_score_band(v):
    """Turn a 0–1 risk/impact score into a plain-language band with a colour
    cue, so a non-expert instantly sees if it's good or bad. Lower = better
    (🟢 less concerning, 🔴 more concerning)."""
    try:
        x = float(v)
    except Exception:
        return str(v)
    if x <= 0.33:
        emoji, band = "🟢", "Low"
    elif x <= 0.66:
        emoji, band = "🟡", "Medium"
    else:
        emoji, band = "🔴", "High"
    return f"{emoji} {band} · {x:.2f}"


def _fmt_priority(v):
    """Priority band aligned to the 0.70 escalate threshold: 🔴 High means the
    score alone is high enough to escalate."""
    try:
        x = float(v)
    except Exception:
        return str(v)
    if x < 0.5:
        emoji, band = "🟢", "Low"
    elif x < 0.7:
        emoji, band = "🟡", "Medium"
    else:
        emoji, band = "🔴", "High"
    return f"{emoji} {band} · {x:.2f}"


# Per-agent headline tiles: (json_field, tile_label, formatter, help_tooltip?).
AGENT_TILES = {
    "reliability": [
        ("risk_classification", "Risk", None),
        ("health_score", "Health", None,
         "Asset health 0–100. Higher is better."),
        ("rul_hours", "RUL (h)", None,
         "Remaining Useful Life — estimated hours until likely failure."),
        ("failure_probability_7d", "P(fail 7d)", None,
         "Probability the asset fails within 7 days (0–1). Lower is better."),
    ],
    "process": [
        ("process_risk", "Process risk", _fmt_score_band,
         "Risk that we can't fix it fast (parts/people/bottlenecks). "
         "🟢 Low is good, 🔴 High is bad."),
        ("parts_available", "Parts", _fmt_bool),
        ("technician_available", "Technician", _fmt_bool),
        ("estimated_response_delay_hours", "Response delay (h)", None,
         "Estimated hours before the team can actually respond."),
    ],
    "cost": [
        ("daily_downtime_cost_usd", "$/day", _fmt_money),
        ("financial_impact_score", "Fin. impact", _fmt_score_band,
         "How much money is at stake (0–1). 🟢 Low stakes, 🔴 High stakes."),
    ],
    "governance": [
        ("overall_decision", "Gate", None),
    ],
}


def _render_tiles(parsed, specs, per_row=2):
    """Lay out headline tiles, max `per_row` per row so values like 'AT_RISK'
    aren't squeezed into a too-narrow column."""
    tiles = []
    for spec in specs:
        field, label, fmt = spec[0], spec[1], spec[2]
        help_txt = spec[3] if len(spec) > 3 else None
        if field in parsed and parsed[field] is not None:
            val = fmt(parsed[field]) if fmt else parsed[field]
            tiles.append((label, val, help_txt))
    for i in range(0, len(tiles), per_row):
        chunk = tiles[i:i + per_row]
        cols = st.columns(len(chunk))
        for col, (label, val, help_txt) in zip(cols, chunk):
            col.metric(label, val, help=help_txt)


def render_agent_body(key, parsed, raw):
    """Render an agent's card content into the current Streamlit context."""
    icon, name, sub = AGENT_META[key]
    st.markdown(f"#### {icon} {name}")
    st.caption(sub)
    if not parsed:
        st.code(raw or "—")
        return

    _render_tiles(parsed, AGENT_TILES.get(key, []), per_row=2)

    # Per-agent callouts / text lines below the tiles.
    if key == "process":
        if parsed.get("bottleneck_description"):
            st.warning(f"**Bottleneck:** {parsed['bottleneck_description']}",
                       icon="⚠️")
        if parsed.get("recommended_workflow_action"):
            st.markdown("**Recommended workflow action:** "
                        f"{parsed['recommended_workflow_action']}")
    elif key == "cost":
        if parsed.get("recommended_intervention_window"):
            st.markdown("**Intervention window:** "
                        f"{parsed['recommended_intervention_window']}")

    st.json(parsed, expanded=False)


def render_final(parsed, raw):
    st.subheader("⚙️ Orchestrator — final decision")
    if not parsed:
        st.code(raw or "—")
        return

    decision = str(parsed.get("autonomous_or_escalate", "")).upper()
    risk = str(parsed.get("risk_level", "")).upper()
    score = parsed.get("priority_score", "—")
    color = RISK_COLOR.get(risk, "#5f5e5a")

    a, b, c = st.columns(3)
    a.metric("Priority score", _fmt_priority(score),
             help="0–1 urgency. ≥0.70 alone is enough to escalate. "
                  "🟢 Low / 🟡 Medium / 🔴 High.")
    b.markdown(
        f"<div style='font-size:12px;color:#888'>RISK LEVEL</div>"
        f"<div style='font-size:26px;font-weight:700;color:{color}'>{risk or '—'}</div>",
        unsafe_allow_html=True,
    )
    if decision == "ESCALATE":
        c.markdown(
            "<div style='font-size:12px;color:#888'>DECISION</div>"
            "<div style='font-size:26px;font-weight:700;color:#A32D2D'>🔺 ESCALATE</div>",
            unsafe_allow_html=True,
        )
    else:
        c.markdown(
            "<div style='font-size:12px;color:#888'>DECISION</div>"
            "<div style='font-size:26px;font-weight:700;color:#3B6D11'>🤖 AUTONOMOUS</div>",
            unsafe_allow_html=True,
        )

    if parsed.get("conflicts_detected"):
        st.warning(f"**Conflict detected:** {parsed['conflicts_detected']}", icon="⚠️")

    st.markdown(
        "<div style='font-size:15px;color:#888;margin-top:12px;"
        "letter-spacing:.5px'>RECOMMENDED ACTION</div>"
        f"<div style='font-size:26px;font-weight:700;line-height:1.35'>"
        f"{parsed.get('recommended_action', '—')}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:15px;color:#888;margin-top:16px;"
        "letter-spacing:.5px'>RATIONALE</div>"
        f"<div style='font-size:21px;line-height:1.5'>"
        f"{parsed.get('rationale', '—')}</div>",
        unsafe_allow_html=True,
    )

    if parsed.get("work_order_draft"):
        with st.expander("📝 Work order draft"):
            st.json(parsed["work_order_draft"])
    st.json(parsed, expanded=False)


# ─────────────────────────────────────────────────────────────────
# Run the crew
# ─────────────────────────────────────────────────────────────────
if run:
    if not GEMINI_API_KEY:
        st.error("Add your GEMINI_API_KEY to the .env file first.", icon="🚫")
        st.stop()

    st.divider()
    st.subheader("🧠 Agents working…")

    # One placeholder per specialist (filled live as each finishes).
    placeholders = {}
    grid = st.columns(2)
    for i, key in enumerate(["reliability", "process", "cost", "governance"]):
        ph = grid[i % 2].empty()
        placeholders[key] = ph
        with ph.container(border=True):
            icon, name, sub = AGENT_META[key]
            st.markdown(f"#### {icon} {name}")
            st.caption(sub)
            st.write("⏳ waiting…")

    final_placeholder = st.container(border=True)

    progress = st.progress(0, text="Dispatching event to the crew…")
    step = {"n": 0}

    def on_task_complete(key, parsed, raw):
        step["n"] += 1
        label = AGENT_META.get(key, ("", "?"))[1]
        progress.progress(min(step["n"] / 5, 1.0),
                          text=f"{label} done ({step['n']}/5)")
        if key in placeholders:
            with placeholders[key].container(border=True):
                render_agent_body(key, parsed, raw)

    with st.spinner("Running the multi-agent crew (this takes ~30–90s)…"):
        result = run_pipeline(event, on_task_complete=on_task_complete)

    progress.progress(1.0, text="Done.")

    # Final decision
    with final_placeholder:
        render_final(result.get("final"), result.get("final_raw"))

    if not result.get("ok"):
        st.error(f"Pipeline issue: {result.get('error')}")

    with st.expander("🔧 Raw crew output (all agents)"):
        st.json({k: v.get("parsed") or v.get("raw") for k, v in result["agents"].items()})

else:
    st.info(
        "Set the trigger event in the sidebar, then click **Run the crew**. "
        "The five agents (Reliability, Process, Cost, Safety & Governance, "
        "Orchestrator) will assess the event and return a prioritized decision.",
        icon="👈",
    )
