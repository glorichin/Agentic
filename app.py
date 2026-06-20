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

from titan_agents import run_pipeline, DEMO_EVENT, GEMINI_API_KEY, GEMINI_MODEL


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
    value = st.number_input("Reading value", value=float(DEMO_EVENT["value"]), step=0.01)
    threshold = st.number_input("Threshold", value=float(DEMO_EVENT["threshold"]), step=0.01)

    st.divider()
    st.markdown("**LLM**")
    st.code(GEMINI_MODEL, language=None)
    if GEMINI_API_KEY:
        st.success(f"API key loaded ({GEMINI_API_KEY[:6]}…)", icon="✅")
    else:
        st.error("No GEMINI_API_KEY in .env", icon="🚫")

    run = st.button("▶  Run the crew", type="primary", use_container_width=True)


event = {
    "event_type": "SENSOR_THRESHOLD_BREACH",
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
    breach = value > threshold
    st.metric(
        label=f"{signal}  ·  {asset_id}",
        value=f"{value}",
        delta=f"{round((value - threshold) / threshold * 100)}% vs threshold {threshold}",
        delta_color="inverse" if breach else "normal",
    )
with c2:
    st.subheader("Event payload")
    st.json(event, expanded=False)


# ─────────────────────────────────────────────────────────────────
# Helpers to render each agent's card
# ─────────────────────────────────────────────────────────────────
def render_agent_body(key, parsed, raw):
    """Render an agent's card content into the current Streamlit context."""
    icon, name, sub = AGENT_META[key]
    st.markdown(f"#### {icon} {name}")
    st.caption(sub)
    if parsed:
        # Highlight a couple of headline numbers when present
        highlights = []
        for field, label in [
            ("risk_classification", "Risk"), ("health_score", "Health"),
            ("rul_hours", "RUL (h)"), ("failure_probability_7d", "P(fail 7d)"),
            ("process_risk", "Process risk"), ("financial_impact_score", "Fin. impact"),
            ("daily_downtime_cost_usd", "$/day"), ("overall_decision", "Gate"),
        ]:
            if field in parsed:
                highlights.append((label, parsed[field]))
        if highlights:
            cols = st.columns(len(highlights))
            for col, (label, val) in zip(cols, highlights):
                col.metric(label, val)
        st.json(parsed, expanded=False)
    else:
        st.code(raw or "—")


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
    a.metric("Priority score", score)
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

    st.markdown(f"**Recommended action:** {parsed.get('recommended_action', '—')}")
    st.markdown(f"**Rationale:** {parsed.get('rationale', '—')}")

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
