"""
titan_agents.py — Titan MIP · Step 3: The Agent Crew (the engine)
─────────────────────────────────────────────────────────────────
This is where the project comes together. It unites:

  • step1_setup.py        → the LLM setup (.env + Gemini via CrewAI)
  • step2_mock_tools.py   → the 12 mock tools the agents call
  • the Agent Prompts     → the 5 CrewAI agents (Orchestrator + 4 others)

and exposes ONE function the demo (Streamlit / Colab) calls:

    run_pipeline(event, on_task_complete=None) -> dict

Architecture: hierarchical intent, run as a reliable SEQUENTIAL pipeline so
every specialist produces a clean, separately-inspectable assessment that the
Orchestrator then synthesizes — perfect for showing each agent's reasoning in
the demo UI.

Usage:
    from titan_agents import run_pipeline, DEMO_EVENT
    result = run_pipeline(DEMO_EVENT)
"""

import os
import json
from dotenv import load_dotenv

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# The team's mock tool layer (Step 2). We wrap these as CrewAI tools below.
import step2_mock_tools as mock


# ═══════════════════════════════════════════════════════════════════
# 1. LLM SETUP  (same approach as step1_setup.py)
# ═══════════════════════════════════════════════════════════════════
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash").strip()

# Free-tier Gemini caps requests per minute (~15). The crew fires many LLM
# calls, so we throttle it below that to avoid 429 RESOURCE_EXHAUSTED errors.
# Lower this if you still hit limits; raise it on a paid key.
MAX_RPM = int(os.getenv("MAX_RPM", "10"))


def build_llm() -> LLM:
    """Create the CrewAI LLM wrapper around Gemini (low temp = consistent
    structured output, exactly like step1_setup.py)."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to the .env file "
            "(get a free key at https://aistudio.google.com/apikey)."
        )
    return LLM(model=GEMINI_MODEL, api_key=GEMINI_API_KEY, temperature=0.1)


# ═══════════════════════════════════════════════════════════════════
# 2. TOOL LAYER  — thin CrewAI wrappers around step2_mock_tools
#
# The agents only need to pass an asset_id: each analytics wrapper fetches
# the readings it depends on internally (from the telemetry/history tools).
# This keeps the ReAct trace authentic — the agent still DECIDES to call each
# tool — while making the live demo robust even with a fast/cheap model.
# "AGENTS DECIDE → TOOLS EXECUTE."
# ═══════════════════════════════════════════════════════════════════

# --- READ tools -----------------------------------------------------

@tool("sensor_telemetry_api")
def sensor_telemetry_api(asset_id: str, window_hours: int = 72) -> str:
    """Fetch recent SCADA/historian sensor readings (vibration, temperature,
    pressure, motor current) for an asset over a time window. Returns each
    reading plus whether it breaches its safe threshold and a data-quality flag."""
    return mock.sensor_telemetry_api(asset_id, window_hours)


@tool("maintenance_history_api")
def maintenance_history_api(asset_id: str, last_n_tickets: int = 10) -> str:
    """Return recent maintenance tickets and a recurring-fault pattern summary
    for an asset. Feeds the agent's episodic memory."""
    return mock.maintenance_history_api(asset_id, last_n_tickets)


@tool("parts_inventory_api")
def parts_inventory_api(asset_id: str, fault_type: str = "bearing") -> str:
    """Check spare-parts availability, on-hand count and lead time for the most
    likely replacement parts for a given asset and fault type."""
    return mock.parts_inventory_api(asset_id, fault_type)


@tool("downtime_cost_calculator")
def downtime_cost_calculator(asset_id: str) -> str:
    """Return the financial impact ($/day and $/hour) of an asset going offline,
    its criticality tier, the production orders depending on it, and SLA risk."""
    return mock.downtime_cost_calculator(asset_id)


# --- ANALYTICS tools (fetch their own inputs, then score) -----------

@tool("anomaly_detector")
def anomaly_detector(asset_id: str) -> str:
    """Run ML anomaly scoring on the asset's current readings. Returns a
    severity score (0-1), a flag (NORMAL/MEDIUM/HIGH/CRITICAL) and the top
    contributing signals so the agent can explain its reasoning."""
    r = json.loads(mock.sensor_telemetry_api(asset_id))["readings"]
    return mock.anomaly_detector(
        asset_id, r["spindle_vibration_g"], r["temp_deviation_pct"], r["motor_current_amp"]
    )


@tool("rul_predictor")
def rul_predictor(asset_id: str) -> str:
    """Estimate Remaining Useful Life (RUL) in hours/days for an asset using a
    degradation model (wear elapsed vs historical bearing life, accelerated by
    how far vibration is above threshold). Returns an urgency band too."""
    r = json.loads(mock.sensor_telemetry_api(asset_id))["readings"]
    s = json.loads(mock.maintenance_history_api(asset_id))["summary"]
    return mock.rul_predictor(
        asset_id, r["spindle_vibration_g"],
        s["last_bearing_change_days_ago"], s["avg_bearing_life_days"]
    )


@tool("asset_health_scorer")
def asset_health_scorer(asset_id: str) -> str:
    """Aggregate anomaly severity, RUL and wear into a single 0-100 asset health
    score and status (HEALTHY/WATCH/AT_RISK/CRITICAL). Lower = worse."""
    r   = json.loads(mock.sensor_telemetry_api(asset_id))["readings"]
    s   = json.loads(mock.maintenance_history_api(asset_id))["summary"]
    an  = json.loads(mock.anomaly_detector(
        asset_id, r["spindle_vibration_g"], r["temp_deviation_pct"], r["motor_current_amp"]))
    rul = json.loads(mock.rul_predictor(
        asset_id, r["spindle_vibration_g"],
        s["last_bearing_change_days_ago"], s["avg_bearing_life_days"]))
    return mock.asset_health_scorer(
        asset_id, an["severity_score"], rul["rul_hours"], rul["life_consumed_pct"]
    )


@tool("root_cause_analyzer")
def root_cause_analyzer(asset_id: str) -> str:
    """Cross-reference current fault signals with historical patterns to surface
    the most likely root cause, secondary factors, a confidence score and a
    recommended fix."""
    r  = json.loads(mock.sensor_telemetry_api(asset_id))["readings"]
    s  = json.loads(mock.maintenance_history_api(asset_id))["summary"]
    an = json.loads(mock.anomaly_detector(
        asset_id, r["spindle_vibration_g"], r["temp_deviation_pct"], r["motor_current_amp"]))
    return mock.root_cause_analyzer(asset_id, an["contributing_signals"], s["pattern_flag"])


# --- ACTION tools (write / execute — some human-gated) --------------

@tool("policy_validator")
def policy_validator(action_type: str, asset_id: str,
                     estimated_cost_usd: float = 0,
                     involves_shutdown: bool = False) -> str:
    """Validate a proposed action against Titan's safety and financial policies
    (the Safety & Governance gate). LOTO override → REJECTED; shutdown →
    REQUIRES_APPROVAL (Plant Manager); cost > $10,000 → REQUIRES_APPROVAL
    (Finance); notify/draft/update → APPROVED (autonomous)."""
    return mock.policy_validator(action_type, asset_id, estimated_cost_usd, involves_shutdown)


@tool("work_order_generator")
def work_order_generator(asset_id: str, fault_description: str,
                         recommended_action: str, priority: str,
                         estimated_downtime_h: int = 4,
                         parts_needed: list = None,
                         technician_skill: str = "Mechanical") -> str:
    """Draft a structured maintenance work order for human review. Status is
    always DRAFT — never auto-executed. parts_needed is a list of dicts with
    part_number, qty, unit_cost_usd."""
    return mock.work_order_generator(
        asset_id, fault_description, recommended_action, priority,
        estimated_downtime_h, parts_needed or [], technician_skill
    )


@tool("notification_service")
def notification_service(recipients: list, subject: str,
                         body: str, priority: str = "HIGH") -> str:
    """Send alert notifications via email and the BMC Helix portal. Autonomously
    executable for MEDIUM/HIGH/CRITICAL alerts. recipients is a list of emails."""
    return mock.notification_service(recipients, subject, body, priority)


@tool("dashboard_updater")
def dashboard_updater(asset_id: str, risk_level: str, health_score: int,
                      recommended_action: str, priority_score: float) -> str:
    """Write the current risk assessment to the BMC Helix maintenance dashboard
    (display only — no action taken). Autonomously executable."""
    return mock.dashboard_updater(asset_id, risk_level, health_score,
                                  recommended_action, priority_score)


# ═══════════════════════════════════════════════════════════════════
# 3. THE 5 AGENTS  (faithful to the Agent Prompts deliverable)
# ═══════════════════════════════════════════════════════════════════

def build_agents(llm: LLM) -> dict:
    """Build all five agents sharing one LLM. Returns a name→Agent dict."""

    orchestrator = Agent(
        role="Maintenance Intelligence Orchestrator",
        goal=(
            "Coordinate the specialists to turn a maintenance event into a single "
            "prioritized, predictive, actionable recommendation, and decide whether "
            "to act autonomously or escalate to a human."
        ),
        backstory=(
            "You are the Maintenance Intelligence Orchestrator for Titan "
            "Manufacturing Corporation. You do not perform analysis yourself — you "
            "synthesize the Reliability, Process, Cost and Safety & Governance "
            "findings into one recommendation.\n\n"
            "You CHECK FOR CONFLICTS between specialist outputs before scoring "
            "(e.g. Cost says defer while Reliability flags urgency, or Process "
            "flags a bottleneck that contradicts the timeline) and state any "
            "conflict explicitly — never resolve it silently inside the formula.\n\n"
            "Priority = (failure_probability x 0.4) + (financial_impact_score x 0.35)"
            " + (process_risk x 0.25). If Safety & Governance flags a risk the "
            "formula does not capture, Safety OVERRIDES the numeric priority — say "
            "so. Decide AUTONOMOUS only if Priority < 0.7 AND the action does not "
            "require machine shutdown, repair approval > $10,000, or a safety "
            "override; otherwise ESCALATE.\n\n"
            "HARD CONSTRAINTS: never take a CNC machine offline without human "
            "approval; never approve repairs > $10,000 autonomously; never average "
            "away a disagreement; always give a rationale the team can challenge; "
            "if Safety & Governance returned REJECTED, stop and notify the plant "
            "manager. You may call work_order_generator, notification_service and "
            "dashboard_updater to execute the actions that were APPROVED."
        ),
        tools=[work_order_generator, notification_service, dashboard_updater],
        llm=llm, verbose=True, allow_delegation=False,
    )

    reliability = Agent(
        role="Reliability Intelligence Agent",
        goal=("Assess the health and failure risk of a specific asset from "
              "telemetry, sensor data and maintenance history."),
        backstory=(
            "You are the Reliability Intelligence Agent for Titan Manufacturing. "
            "Your SOLE job is to assess asset health and failure risk — you do not "
            "take actions. On every request you call: sensor_telemetry_api, then "
            "anomaly_detector, then maintenance_history_api, then rul_predictor, "
            "then asset_health_scorer. Do NOT call work_order_generator or "
            "notification_service.\n\n"
            "Reasoning rules: vibration > 0.35g on rotating equipment → AT_RISK "
            "minimum; temperature > 15% above baseline → flag anomaly; RUL < 72h "
            "AND anomaly_severity > 0.8 AND failure_probability > 0.6 → CRITICAL. "
            "Always cite the specific sensor signal driving your highest concern. "
            "If telemetry is stale (>15 min) or missing, flag a data-quality issue "
            "and defer rather than guessing."
        ),
        tools=[sensor_telemetry_api, anomaly_detector, maintenance_history_api,
               rul_predictor, asset_health_scorer],
        llm=llm, verbose=True, allow_delegation=False,
    )

    process = Agent(
        role="Process Intelligence Agent",
        goal=("Assess the maintenance workflow itself — parts, technicians and "
              "recurring process bottlenecks — that could slow or block a fix even "
              "when the technical recommendation is correct."),
        backstory=(
            "You are the Process Intelligence Agent for Titan Manufacturing. You "
            "assess how efficiently the organization can respond once a risk is "
            "identified — not the machine's health. You do not take actions. On "
            "every request you call: maintenance_history_api (how past issues were "
            "handled and how long they took), parts_inventory_api (availability + "
            "lead time), and root_cause_analyzer (does this match a recurring "
            "process pattern?). Then identify the single largest bottleneck risk.\n\n"
            "Reasoning rules: if parts lead time exceeds the asset's RUL → "
            "process_risk HIGH regardless of other factors, flag prominently; if no "
            "technician is available this/next shift → bottleneck even if parts are "
            "ready; if the asset has a documented history of repeated process "
            "delays, state the pattern explicitly. Output a numeric process_risk "
            "(0-1)."
        ),
        tools=[maintenance_history_api, parts_inventory_api, root_cause_analyzer],
        llm=llm, verbose=True, allow_delegation=False,
    )

    cost = Agent(
        role="Cost Intelligence Agent",
        goal=("Quantify the business and financial impact of a potential asset "
              "failure — money, production loss and delivery impact."),
        backstory=(
            "You are the Cost Intelligence Agent for Titan Manufacturing. You "
            "translate reliability risk into money. On every request you call "
            "downtime_cost_calculator for the daily cost and the production orders "
            "at risk, and parts_inventory_api to estimate parts cost. You estimate "
            "cost_of_failure_now = rul_hours / 24 x daily_downtime_cost; "
            "cost_of_planned_maintenance = parts_cost + labour; "
            "roi = cost_of_failure_now - cost_of_planned_maintenance. You assign a "
            "financial_impact_score (0-1) by daily-cost tier: > $150,000/day → 1.0;"
            " $50,000-$150,000 → 0.7; $10,000-$50,000 → 0.4; < $10,000 → 0.2. You "
            "do not take actions."
        ),
        tools=[downtime_cost_calculator, parts_inventory_api],
        llm=llm, verbose=True, allow_delegation=False,
    )

    governance = Agent(
        role="Safety & Governance Agent",
        goal=("Act as the final gate before any action is executed: ensure every "
              "proposed action complies with safety, financial and operational "
              "policy."),
        backstory=(
            "You are the Safety & Governance Agent for Titan Manufacturing — the "
            "FINAL GATE before any action runs. You do not assess machine health; "
            "you assess whether a proposed action is safe and authorized. For each "
            "proposed action call policy_validator. Rules: machine shutdown → "
            "REQUIRES_APPROVAL (Plant Manager); repair cost > $10,000 → "
            "REQUIRES_APPROVAL (Finance); LOTO override → REJECTED; "
            "alert/notify/draft work order/update dashboard → APPROVED (autonomous);"
            " vendor intervention on a critical asset → REQUIRES_APPROVAL. Return a "
            "clear decision per action plus the approver required, the policy "
            "references checked, and any risk flags."
        ),
        tools=[policy_validator],
        llm=llm, verbose=True, allow_delegation=False,
    )

    return {
        "orchestrator": orchestrator,
        "reliability":  reliability,
        "process":      process,
        "cost":         cost,
        "governance":   governance,
    }


# ═══════════════════════════════════════════════════════════════════
# 4. THE PIPELINE  (tasks + crew + runner)
# ═══════════════════════════════════════════════════════════════════

DEMO_EVENT = {
    "event_type": "SENSOR_THRESHOLD_BREACH",
    "asset_id":   os.getenv("DEMO_ASSET_ID", "CNC-Lathe-07"),
    "plant":      os.getenv("DEMO_PLANT", "Plant 3 - Valencia"),
    "signal":     "spindle_vibration",
    "value":      0.48,
    "threshold":  0.35,
    "timestamp":  "2026-06-20T07:14:33Z",
}


def build_crew(event: dict, agents: dict, task_callback=None) -> Crew:
    """Build the 5-task sequential crew for a given trigger event.
    Specialists assess first; Governance gates; the Orchestrator synthesizes."""
    ev = json.dumps(event, indent=2)
    aid = event["asset_id"]

    reliability_task = Task(
        description=(
            f"A maintenance event was received:\n{ev}\n\n"
            f"Assess the health and failure risk of asset {aid}. Use your tools "
            "(telemetry, anomaly detection, history, RUL, health score)."
        ),
        expected_output=(
            "A compact JSON object: asset_id, health_score (0-100), "
            "risk_classification (HEALTHY/WATCH/AT_RISK/CRITICAL), anomaly_severity "
            "(0-1), rul_hours, failure_probability_7d (0-1), key_signals (list), "
            "historical_pattern (one sentence)."
        ),
        agent=agents["reliability"],
    )

    process_task = Task(
        description=(
            f"For the same event on asset {aid}, assess the maintenance WORKFLOW: "
            "parts availability and lead time, technician availability, and whether "
            "this matches a recurring process bottleneck. Identify the single "
            "largest bottleneck risk."
        ),
        expected_output=(
            "A compact JSON object: asset_id, parts_available (bool), "
            "parts_lead_time_hours, technician_available (bool), "
            "estimated_response_delay_hours, bottleneck_detected (bool), "
            "bottleneck_description, process_risk (0-1), recommended_workflow_action."
        ),
        agent=agents["process"],
    )

    cost_task = Task(
        description=(
            f"For the same event on asset {aid}, quantify the financial and "
            "business impact: daily downtime cost, orders at risk, cost of failure "
            "now vs planned maintenance, ROI of intervening now, and a financial "
            "impact score."
        ),
        expected_output=(
            "A compact JSON object: asset_id, daily_downtime_cost_usd, "
            "cost_of_failure_now_usd, cost_of_planned_maintenance_usd, "
            "roi_of_intervention_usd, financial_impact_score (0-1), "
            "production_orders_at_risk, recommended_intervention_window."
        ),
        agent=agents["cost"],
    )

    governance_task = Task(
        description=(
            f"Using the Reliability, Process and Cost assessments, review the "
            f"actions that would typically be proposed for asset {aid}: "
            "(1) draft a work order, (2) notify the maintenance lead, "
            "(3) update the dashboard, and (4) a recommended machine shutdown "
            "window for the repair. Call policy_validator for each and return the "
            "decision per action."
        ),
        expected_output=(
            "A compact JSON object: per_action (list of {action_type, decision, "
            "approver_required}), overall_decision "
            "(APPROVED/REQUIRES_APPROVAL/REJECTED), policy_references (list), "
            "risk_flags (list)."
        ),
        agent=agents["governance"],
        context=[reliability_task, process_task, cost_task],
    )

    orchestrator_task = Task(
        description=(
            f"Synthesize all four assessments for asset {aid}. First CHECK FOR "
            "CONFLICTS between specialists and state them. Then compute "
            "Priority = failure_probability_7d*0.4 + financial_impact_score*0.35 + "
            "process_risk*0.25. Apply the Safety override if Governance flagged "
            "anything the formula misses. Decide AUTONOMOUS vs ESCALATE per the "
            "hard constraints (a CNC machine is never taken offline autonomously; "
            "repairs > $10,000 always escalate; a Governance REJECTED stops "
            "everything). Then EXECUTE the autonomous-approved actions by calling "
            "work_order_generator, notification_service and dashboard_updater."
        ),
        expected_output=(
            "A single JSON object with: asset_id, plant, priority_score (0-1), "
            "risk_level (LOW/MEDIUM/HIGH/CRITICAL), conflicts_detected (string, "
            "empty if none), recommended_action, autonomous_or_escalate "
            "(AUTONOMOUS/ESCALATE), rationale (2-3 sentences incl. how any conflict "
            "was resolved), work_order_draft (object or null), next_check_in (ISO "
            "timestamp)."
        ),
        agent=agents["orchestrator"],
        context=[reliability_task, process_task, cost_task, governance_task],
    )

    return Crew(
        agents=[agents["reliability"], agents["process"], agents["cost"],
                agents["governance"], agents["orchestrator"]],
        tasks=[reliability_task, process_task, cost_task,
               governance_task, orchestrator_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=MAX_RPM,          # throttle to stay under the free-tier limit
        task_callback=task_callback,
    )


def parse_json(text: str):
    """Leniently parse a JSON object out of an LLM response (handles ```json
    fences and surrounding prose). Returns dict, or None if not parseable."""
    if text is None:
        return None
    s = str(text).strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    try:
        return json.loads(s)
    except Exception:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except Exception:
                return None
    return None


# Maps task order → friendly agent key (CrewAI returns tasks_output in order).
_TASK_ORDER = ["reliability", "process", "cost", "governance", "orchestrator"]


def run_pipeline(event: dict = None, on_task_complete=None) -> dict:
    """Run the full Titan MIP crew on a trigger event.

    Args:
        event: trigger event dict (defaults to DEMO_EVENT / CNC-Lathe-07).
        on_task_complete: optional callback(agent_key, parsed_or_None, raw_text)
                          fired as each agent finishes — used for live UI updates.

    Returns:
        dict with keys: event, agents {key: {raw, parsed}}, final (parsed
        orchestrator output), final_raw, ok (bool).
    """
    event = event or DEMO_EVENT
    llm = build_llm()
    agents = build_agents(llm)

    completed = {"i": 0}

    def _cb(task_output):
        idx = completed["i"]
        key = _TASK_ORDER[idx] if idx < len(_TASK_ORDER) else f"task_{idx}"
        completed["i"] += 1
        if on_task_complete:
            raw = getattr(task_output, "raw", str(task_output))
            on_task_complete(key, parse_json(raw), raw)

    crew = build_crew(event, agents, task_callback=_cb)
    result = crew.kickoff()

    out = {"event": event, "agents": {}, "final": None, "final_raw": "", "ok": True}
    try:
        for key, t in zip(_TASK_ORDER, result.tasks_output):
            raw = getattr(t, "raw", str(t))
            out["agents"][key] = {"raw": raw, "parsed": parse_json(raw)}
        out["final_raw"] = out["agents"].get("orchestrator", {}).get("raw", str(result))
        out["final"] = out["agents"].get("orchestrator", {}).get("parsed")
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)
        out["final_raw"] = str(result)
    return out


if __name__ == "__main__":
    print("Running Titan MIP crew on the demo event...\n")
    res = run_pipeline(DEMO_EVENT)
    print("\n" + "=" * 64)
    print("ORCHESTRATOR DECISION")
    print("=" * 64)
    print(json.dumps(res["final"], indent=2) if res["final"] else res["final_raw"])
