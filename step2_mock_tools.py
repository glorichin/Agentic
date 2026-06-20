"""
step2_mock_tools.py — Titan MIP Mock Tool Layer
─────────────────────────────────────────────────────────────
All 12 tools the CrewAI agents will call during the demo.
In a real deployment these would hit live SCADA APIs, the CMMS,
parts inventory systems, vendor portals, etc.

For the demo they return realistic, deterministic data so the
agents can reason over them authentically without needing
real OT infrastructure.

Core assignment rule:
    AGENTS DECIDE  →  TOOLS EXECUTE
These functions are the "execute" side — they never decide anything.

Usage:
    python3 step2_mock_tools.py          ← runs smoke test
    from step2_mock_tools import *       ← import into agents file (Step 3)
"""

import json
import random
import sys
from datetime import datetime, timedelta, timezone

# Windows consoles default to a codepage that can't render the ✓/✗/─
# symbols in the smoke test below — force UTF-8 so it runs unmodified everywhere.
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _future_iso(hours: int) -> str:
    t = datetime.now(timezone.utc) + timedelta(hours=hours)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")

def _jdump(obj: dict) -> str:
    """Return pretty JSON string — CrewAI tools must return strings."""
    return json.dumps(obj, indent=2)


# ═══════════════════════════════════════════════════════════
# DATA TOOLS  (read-only)
# ═══════════════════════════════════════════════════════════

def sensor_telemetry_api(asset_id: str, window_hours: int = 72) -> str:
    """
    Fetch recent sensor readings for an asset from SCADA / historian.

    Returns vibration (g), temperature (°C), pressure (bar) and motor
    current (A) — the four key signals for CNC spindle health.
    Also flags whether each reading exceeds its safe operating threshold.

    Args:
        asset_id:     Asset identifier, e.g. "CNC-Lathe-07"
        window_hours: How many hours of history to summarise (default 72)
    """
    if asset_id == "CNC-Lathe-07":
        # Demo asset — in a degraded state to drive the scenario
        data = {
            "spindle_vibration_g":          0.48,
            "vibration_threshold_g":        0.35,
            "vibration_above_threshold":     True,
            "hours_above_threshold":         3.2,
            "temperature_c":                87.3,
            "baseline_temp_c":              74.0,
            "temp_deviation_pct":           18.0,
            "pressure_bar":                  3.1,
            "pressure_nominal_bar":          3.5,
            "motor_current_amp":            22.4,
            "motor_current_nominal_amp":    20.0,
            "trend":                        "increasing",
            "data_quality":                 "GOOD",
            "data_age_minutes":              2,
        }
    else:
        random.seed(hash(asset_id) % 9999)
        vib = round(random.uniform(0.10, 0.28), 2)
        data = {
            "spindle_vibration_g":         vib,
            "vibration_threshold_g":       0.35,
            "vibration_above_threshold":   vib > 0.35,
            "hours_above_threshold":       0,
            "temperature_c":               round(random.uniform(68, 76), 1),
            "baseline_temp_c":             74.0,
            "temp_deviation_pct":          round(random.uniform(-5, 4), 1),
            "pressure_bar":                round(random.uniform(3.3, 3.6), 2),
            "pressure_nominal_bar":        3.5,
            "motor_current_amp":           round(random.uniform(18.5, 20.5), 1),
            "motor_current_nominal_amp":   20.0,
            "trend":                       "stable",
            "data_quality":                "GOOD",
            "data_age_minutes":            2,
        }

    return _jdump({
        "asset_id":     asset_id,
        "window_hours": window_hours,
        "timestamp":    _now_iso(),
        "readings":     data,
    })


def maintenance_history_api(asset_id: str, last_n_tickets: int = 10) -> str:
    """
    Return recent maintenance tickets and a pattern summary for an asset.

    Feeds the agent's episodic memory — helps it spot recurring faults
    that raw telemetry alone cannot reveal.

    Args:
        asset_id:        Asset identifier
        last_n_tickets:  How many recent tickets to return (default 10)
    """
    if asset_id == "CNC-Lathe-07":
        tickets = [
            {
                "ticket_id":   "TIT-2026-3981",
                "date":        "2026-04-02",
                "fault":       "Spindle bearing replacement (SKF 6208)",
                "downtime_h":  6,
                "cost_usd":    2_400,
                "root_cause":  "Normal wear — 8,200 operating hours",
                "resolution":  "Bearing replaced, vibration returned to 0.18g",
            },
            {
                "ticket_id":   "TIT-2026-3612",
                "date":        "2026-02-14",
                "fault":       "Spindle bearing replacement (SKF 6208)",
                "downtime_h":  5,
                "cost_usd":    2_200,
                "root_cause":  "Premature wear — possible misalignment",
                "resolution":  "Bearing replaced, alignment check performed",
            },
            {
                "ticket_id":   "TIT-2026-3204",
                "date":        "2025-12-01",
                "fault":       "Unplanned shutdown — vibration alarm",
                "downtime_h":  14,
                "cost_usd":    105_000,
                "root_cause":  "Bearing failure — not predicted in time",
                "resolution":  "Emergency repair, production order delayed 2 days",
            },
            {
                "ticket_id":   "TIT-2025-2890",
                "date":        "2025-09-18",
                "fault":       "Coolant pressure low",
                "downtime_h":  2,
                "cost_usd":    800,
                "root_cause":  "Pump seal wear",
                "resolution":  "Seal replaced",
            },
        ]
        summary = {
            "recurring_fault":              "Spindle bearing wear (3 occurrences in 9 months)",
            "avg_bearing_life_days":        82,
            "last_bearing_change_days_ago": 79,
            "total_downtime_ytd_h":         27,
            "total_cost_ytd_usd":           110_400,
            "pattern_flag":  "BEARING_ACCELERATED_WEAR — replacement intervals shortening",
        }
    else:
        tickets = [
            {
                "ticket_id":  f"TIT-2026-{3000 + i}",
                "date":       "2026-05-01",
                "fault":      "Routine PM",
                "downtime_h": 2,
                "cost_usd":   500,
                "root_cause": "Scheduled",
                "resolution": "Completed OK",
            }
            for i in range(2)
        ]
        summary = {
            "recurring_fault":              "None",
            "avg_bearing_life_days":        180,
            "last_bearing_change_days_ago": 45,
            "total_downtime_ytd_h":         4,
            "total_cost_ytd_usd":           1_000,
            "pattern_flag":                 "NONE",
        }

    return _jdump({
        "asset_id":  asset_id,
        "tickets":   tickets[:last_n_tickets],
        "summary":   summary,
        "timestamp": _now_iso(),
    })


def parts_inventory_api(asset_id: str, fault_type: str = "bearing") -> str:
    """
    Check spare parts availability for the most likely replacement parts.

    Args:
        asset_id:   Asset identifier
        fault_type: Type of fault to look up parts for (e.g. "bearing")
    """
    if "Lathe-07" in asset_id or "bearing" in fault_type.lower():
        parts = [
            {
                "part_number":    "SKF-6208-2RS",
                "description":    "Deep groove ball bearing 40×80×18 mm",
                "on_hand":        3,
                "location":       "Warehouse B, Shelf 4-C",
                "unit_cost_usd":  87,
                "lead_time_days": 0,
            },
            {
                "part_number":    "CASTROL-OPTIEB-5",
                "description":    "Spindle bearing grease, 5 kg",
                "on_hand":        8,
                "location":       "Warehouse B, Shelf 2-A",
                "unit_cost_usd":  45,
                "lead_time_days": 0,
            },
        ]
        availability = "IN_STOCK"
    else:
        parts        = []
        availability = "NOT_FOUND — request manual warehouse check"

    return _jdump({
        "asset_id":    asset_id,
        "fault_type":  fault_type,
        "availability": availability,
        "parts":       parts,
        "timestamp":   _now_iso(),
    })


def downtime_cost_calculator(asset_id: str) -> str:
    """
    Return the financial impact of this asset going offline and which
    production orders are currently depending on it.

    Args:
        asset_id: Asset identifier
    """
    costs = {
        "CNC-Lathe-07":  {"daily_usd": 180_000, "tier": "TIER_1"},
        "CNC-Lathe-03":  {"daily_usd":  95_000, "tier": "TIER_1"},
        "Robot-Cell-12": {"daily_usd":  42_000, "tier": "TIER_2"},
        "Conveyor-B4":   {"daily_usd":  18_000, "tier": "TIER_2"},
    }
    info = costs.get(asset_id, {"daily_usd": 12_000, "tier": "TIER_3"})

    if asset_id == "CNC-Lathe-07":
        orders = [
            {
                "order_id":  "ORD-2026-8841",
                "customer":  "Airbus Valencia",
                "due_date":  "2026-06-24",
                "parts_needed": 48,
            },
            {
                "order_id":  "ORD-2026-8902",
                "customer":  "Rolls-Royce Derby",
                "due_date":  "2026-06-25",
                "parts_needed": 16,
            },
            {
                "order_id":  "ORD-2026-9011",
                "customer":  "Titan Internal",
                "due_date":  "2026-06-27",
                "parts_needed": 120,
            },
        ]
        sla_risk = "HIGH — Airbus order due in 4 days"
    else:
        orders   = []
        sla_risk = "LOW"

    return _jdump({
        "asset_id":                  asset_id,
        "daily_downtime_cost_usd":   info["daily_usd"],
        "hourly_cost_usd":           round(info["daily_usd"] / 24),
        "criticality_tier":          info["tier"],
        "production_orders_at_risk": orders,
        "sla_breach_risk":           sla_risk,
        "timestamp":                 _now_iso(),
    })


# ═══════════════════════════════════════════════════════════
# ANALYTICS TOOLS  (compute / ML)
# ═══════════════════════════════════════════════════════════

def anomaly_detector(asset_id: str, vibration_g: float,
                     temp_deviation_pct: float,
                     motor_current_amp: float) -> str:
    """
    Score the current sensor readings for anomaly severity (0–1).

    Weights: vibration 45%, temperature 30%, current 25%.
    Returns a flag (NORMAL / ANOMALY_MEDIUM / ANOMALY_HIGH / ANOMALY_CRITICAL)
    and the top contributing signals so the agent can explain its reasoning.

    Args:
        asset_id:           Asset identifier
        vibration_g:        Current spindle vibration in g
        temp_deviation_pct: % deviation from baseline temperature
        motor_current_amp:  Current motor draw in amps
    """
    score        = 0.0
    contributing = []

    if vibration_g > 0.35:
        contrib = min((vibration_g - 0.35) / 0.35, 1.0)
        score  += 0.45 * contrib
        contributing.append(
            f"Spindle vibration {vibration_g}g — {round(contrib*100)}% above threshold"
        )

    if temp_deviation_pct > 10:
        contrib = min((temp_deviation_pct - 10) / 20, 1.0)
        score  += 0.30 * contrib
        contributing.append(
            f"Temperature {round(temp_deviation_pct, 1)}% above baseline"
        )

    if motor_current_amp > 21:
        contrib = min((motor_current_amp - 20) / 5, 1.0)
        score  += 0.25 * contrib
        contributing.append(
            f"Motor current {motor_current_amp}A — elevated load"
        )

    score = round(min(score, 1.0), 3)

    if score >= 0.75:   flag = "ANOMALY_CRITICAL"
    elif score >= 0.50: flag = "ANOMALY_HIGH"
    elif score >= 0.25: flag = "ANOMALY_MEDIUM"
    else:               flag = "NORMAL"

    return _jdump({
        "asset_id":            asset_id,
        "anomaly_detected":    score >= 0.25,
        "severity_score":      score,
        "flag":                flag,
        "contributing_signals": contributing,
        "model_version":       "anomaly-v2.3",
        "timestamp":           _now_iso(),
    })


def rul_predictor(asset_id: str, vibration_g: float,
                  last_bearing_change_days_ago: int,
                  avg_bearing_life_days: int) -> str:
    """
    Estimate Remaining Useful Life (RUL) in hours.

    Uses a degradation model: compares elapsed life against historical
    average bearing life, then accelerates the estimate based on how far
    vibration is above threshold (higher vibration = faster wear).

    Args:
        asset_id:                    Asset identifier
        vibration_g:                 Current vibration in g
        last_bearing_change_days_ago: Days since last bearing replacement
        avg_bearing_life_days:       Historical average life for this asset
    """
    life_consumed    = min(last_bearing_change_days_ago / avg_bearing_life_days, 1.0)
    vibration_factor = 1.0
    if vibration_g > 0.35:
        # Each 0.2g above threshold doubles the wear rate (capped at 3×)
        vibration_factor = min(1 + (vibration_g - 0.35) / 0.20, 3.0)

    remaining_days = (1 - life_consumed) * avg_bearing_life_days / vibration_factor
    rul_hours      = max(round(remaining_days * 24), 0)

    if rul_hours <= 24:    urgency = "IMMEDIATE"
    elif rul_hours <= 72:  urgency = "URGENT"
    elif rul_hours <= 168: urgency = "PLAN_THIS_WEEK"
    else:                  urgency = "MONITOR"

    return _jdump({
        "asset_id":              asset_id,
        "rul_hours":             rul_hours,
        "rul_days":              round(rul_hours / 24, 1),
        "urgency":               urgency,
        "life_consumed_pct":     round(life_consumed * 100, 1),
        "vibration_factor":      round(vibration_factor, 2),
        "model_version":         "rul-v1.8",
        "recommended_action_by": _future_iso(min(rul_hours, 48)),
        "timestamp":             _now_iso(),
    })


def asset_health_scorer(asset_id: str, anomaly_severity: float,
                        rul_hours: int, life_consumed_pct: float) -> str:
    """
    Aggregate anomaly score, RUL, and wear into a single 0–100 health score.
    Lower = worse. Weights: anomaly 45%, RUL 35%, wear 20%.

    Args:
        asset_id:           Asset identifier
        anomaly_severity:   Score from anomaly_detector (0–1)
        rul_hours:          Remaining Useful Life in hours
        life_consumed_pct:  % of bearing life elapsed
    """
    anomaly_component = round((1 - anomaly_severity) * 100)
    rul_component     = round(min(rul_hours / 720, 1.0) * 100)   # 720h = 30 days = perfect
    wear_component    = round((1 - life_consumed_pct / 100) * 100)

    health = round(
        anomaly_component * 0.45 +
        rul_component     * 0.35 +
        wear_component    * 0.20
    )

    if health >= 75:   status = "HEALTHY"
    elif health >= 50: status = "WATCH"
    elif health >= 25: status = "AT_RISK"
    else:              status = "CRITICAL"

    return _jdump({
        "asset_id":     asset_id,
        "health_score": health,
        "status":       status,
        "component_scores": {
            "anomaly_component": anomaly_component,
            "rul_component":     rul_component,
            "wear_component":    wear_component,
        },
        "timestamp": _now_iso(),
    })


def root_cause_analyzer(asset_id: str, fault_signals: list,
                        historical_pattern: str) -> str:
    """
    Cross-reference current signals with historical fault patterns
    to surface the most likely root cause and recommended fix.

    Args:
        asset_id:            Asset identifier
        fault_signals:       List of contributing signals from anomaly_detector
        historical_pattern:  Pattern flag from maintenance_history_api summary
    """
    sig_str = str(fault_signals).lower()

    if "bearing" in historical_pattern.lower() or "vibration" in sig_str:
        primary     = "Spindle bearing fatigue — accelerated wear pattern"
        secondary   = [
            "Possible misalignment from last bearing installation (Feb 2026)",
            "Operating at 79 days — exceeding historical 68-day failure interval",
        ]
        confidence  = 0.87
        fix         = "Replace spindle bearing (SKF 6208) and perform alignment check"
        similar     = 3
    else:
        primary     = "Unknown — insufficient pattern match for automated diagnosis"
        secondary   = ["Manual technician inspection required"]
        confidence  = 0.40
        fix         = "Manual inspection before any action"
        similar     = 0

    return _jdump({
        "asset_id":          asset_id,
        "primary_cause":     primary,
        "secondary_factors": secondary,
        "confidence":        confidence,
        "recommended_fix":   fix,
        "similar_past_cases": similar,
        "timestamp":         _now_iso(),
    })


# ═══════════════════════════════════════════════════════════
# ACTION TOOLS  (write / execute — some human-gated)
# ═══════════════════════════════════════════════════════════

def work_order_generator(asset_id: str, fault_description: str,
                         recommended_action: str, priority: str,
                         estimated_downtime_h: int, parts_needed: list,
                         technician_skill: str = "Mechanical") -> str:
    """
    Draft a structured maintenance work order for human review.
    Status is always DRAFT — never auto-executed.

    Args:
        asset_id:              Asset to be maintained
        fault_description:     What is wrong
        recommended_action:    What should be done
        priority:              CRITICAL / HIGH / MEDIUM / LOW
        estimated_downtime_h:  Expected hours offline
        parts_needed:          List of dicts with part_number, qty, unit_cost_usd
        technician_skill:      Skill category required
    """
    wo_id = f"TIT-2026-{4400 + abs(hash(asset_id)) % 100}"

    parts_cost      = sum(p.get("unit_cost_usd", 0) * p.get("qty", 1) for p in parts_needed)
    labour_cost     = estimated_downtime_h * 85   # €85/hr technician rate
    total_cost      = parts_cost + labour_cost + 1_800  # overhead

    return _jdump({
        "status":                 "DRAFT — awaiting maintenance lead approval",
        "work_order_id":          wo_id,
        "created_at":             _now_iso(),
        "asset_id":               asset_id,
        "plant":                  "Plant 3 - Valencia",
        "priority":               priority,
        "fault_description":      fault_description,
        "recommended_action":     recommended_action,
        "estimated_downtime_h":   estimated_downtime_h,
        "planned_start":          _future_iso(2),
        "planned_completion":     _future_iso(2 + estimated_downtime_h),
        "parts_required":         parts_needed,
        "technician_skill":       technician_skill,
        "assigned_to":            "Ana García — Mechanical Lead, Valencia",
        "estimated_cost_usd":     total_cost,
        "requires_approval_from": "Maintenance Lead (any action) + Plant Manager (if shutdown)",
    })


def notification_service(recipients: list, subject: str,
                         body: str, priority: str = "HIGH") -> str:
    """
    Send alert notifications via email and the BMC Helix portal.
    Autonomously executable for MEDIUM / HIGH / CRITICAL alerts.

    Args:
        recipients: List of email addresses
        subject:    Notification subject line
        body:       Message body
        priority:   LOW / MEDIUM / HIGH / CRITICAL
    """
    return _jdump({
        "status":     "SENT",
        "recipients": recipients,
        "subject":    subject,
        "priority":   priority,
        "channels":   ["email", "BMC Helix portal notification"],
        "sent_at":    _now_iso(),
        "message_id": f"MSG-{abs(hash(subject)) % 99999:05d}",
    })


def dashboard_updater(asset_id: str, risk_level: str,
                      health_score: int, recommended_action: str,
                      priority_score: float) -> str:
    """
    Write the current risk assessment to the BMC Helix maintenance dashboard.
    Autonomously executable — display only, no action taken.

    Args:
        asset_id:           Asset identifier
        risk_level:         HEALTHY / WATCH / AT_RISK / CRITICAL
        health_score:       0–100
        recommended_action: Text to display on the dashboard card
        priority_score:     Orchestrator priority score 0–1
    """
    colour = {
        "CRITICAL": "RED",
        "AT_RISK":  "ORANGE",
        "WATCH":    "YELLOW",
        "HEALTHY":  "GREEN",
    }.get(risk_level, "GREY")

    return _jdump({
        "status":    "UPDATED",
        "dashboard": "BMC Helix — Maintenance Intelligence Platform",
        "card": {
            "asset_id":           asset_id,
            "health_score":       health_score,
            "risk_level":         risk_level,
            "status_colour":      colour,
            "recommended_action": recommended_action,
            "priority_score":     round(priority_score, 3),
            "last_updated":       _now_iso(),
            "next_refresh":       _future_iso(2),
        },
    })


def policy_validator(action_type: str, asset_id: str,
                     estimated_cost_usd: float = 0,
                     involves_shutdown: bool = False) -> str:
    """
    Validate a proposed action against Titan's safety and financial policies.
    This is the Safety & Governance gate — the agent calls this before
    executing any action.

    Decision logic:
      - LOTO override          → always REJECTED
      - Machine shutdown        → REQUIRES_APPROVAL (Plant Manager)
      - Cost > $10,000          → REQUIRES_APPROVAL (Finance Controller)
      - Notify / draft / update → APPROVED (autonomous)

    Args:
        action_type:          e.g. DRAFT_WORK_ORDER, NOTIFY, MACHINE_SHUTDOWN
        asset_id:             Asset the action applies to
        estimated_cost_usd:   Expected cost of the action
        involves_shutdown:    True if the action takes a machine offline
    """
    decision = "APPROVED"
    reason   = "Action within autonomous authority bounds."
    approver = None
    flags    = []

    # Hard block — safety critical
    if action_type == "LOTO_OVERRIDE":
        return _jdump({
            "decision":          "REJECTED",
            "decision_reason":   "LOTO override is never permitted autonomously. Stop immediately.",
            "approver_required": "Safety Officer — mandatory",
            "action_type":       action_type,
            "policy_references": ["HS-004: Lockout/Tagout procedures"],
            "risk_flags":        ["SAFETY_CRITICAL: LOTO override blocked"],
            "timestamp":         _now_iso(),
        })

    if involves_shutdown:
        decision = "REQUIRES_APPROVAL"
        reason   = "Machine shutdown requires Plant Manager authorisation."
        approver = "Plant Manager — Valencia"
        flags.append("SHUTDOWN_RISK: Production orders may be impacted")

    if estimated_cost_usd > 10_000:
        decision = "REQUIRES_APPROVAL"
        reason   = f"Cost ${estimated_cost_usd:,.0f} exceeds $10,000 autonomous threshold."
        approver = (approver + " + " if approver else "") + "Finance Controller"
        flags.append(f"COST_APPROVAL: ${estimated_cost_usd:,.0f} requires finance sign-off")

    autonomous_ok = {"NOTIFY", "DRAFT_WORK_ORDER", "UPDATE_DASHBOARD", "ALERT"}
    if action_type in autonomous_ok and decision == "APPROVED":
        reason = f"{action_type} is within autonomous execution scope — no approval needed."

    return _jdump({
        "decision":          decision,
        "decision_reason":   reason,
        "approver_required": approver,
        "action_type":       action_type,
        "policy_references": [
            "OP-MAINT-001: Predictive maintenance autonomy bounds",
            "FIN-AUTH-012: Repair cost approval thresholds",
            "HS-004: Lockout/Tagout procedures",
        ],
        "risk_flags": flags,
        "timestamp":  _now_iso(),
    })


# ═══════════════════════════════════════════════════════════
# SMOKE TEST  — run directly to verify all 12 tools
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":

    ASSET = "CNC-Lathe-07"

    print("\n" + "="*60)
    print("  TITAN MIP — Step 2: Mock Tool Smoke Test")
    print(f"  Asset: {ASSET}  |  Plant 3 - Valencia")
    print("="*60)

    errors = []

    def check(label, result_json, *assertions):
        """Run assertions on a tool result and report pass/fail."""
        try:
            data = json.loads(result_json)
            for fn, msg in assertions:
                assert fn(data), msg
            print(f"  ✓  {label}")
            return data
        except Exception as e:
            print(f"  ✗  {label} — {e}")
            errors.append(label)
            return {}

    print("\n  ── Data tools ──────────────────────────────────")

    # 1. Telemetry
    tel = check(
        "[1] sensor_telemetry_api",
        sensor_telemetry_api(ASSET),
        (lambda d: d["readings"]["spindle_vibration_g"] == 0.48, "vibration should be 0.48g"),
        (lambda d: d["readings"]["vibration_above_threshold"] is True, "should be above threshold"),
    )
    vib      = tel.get("readings", {}).get("spindle_vibration_g", 0.48)
    temp_dev = tel.get("readings", {}).get("temp_deviation_pct", 18.0)
    current  = tel.get("readings", {}).get("motor_current_amp", 22.4)

    # 2. Maintenance history
    hist = check(
        "[2] maintenance_history_api",
        maintenance_history_api(ASSET),
        (lambda d: "BEARING" in d["summary"]["pattern_flag"], "should flag bearing wear"),
        (lambda d: d["summary"]["last_bearing_change_days_ago"] == 79, "should be 79 days"),
    )
    avg_life  = hist.get("summary", {}).get("avg_bearing_life_days", 82)
    days_ago  = hist.get("summary", {}).get("last_bearing_change_days_ago", 79)
    pattern   = hist.get("summary", {}).get("pattern_flag", "")

    # 3. Parts inventory
    check(
        "[3] parts_inventory_api",
        parts_inventory_api(ASSET, "bearing"),
        (lambda d: d["availability"] == "IN_STOCK", "bearing should be in stock"),
        (lambda d: len(d["parts"]) >= 2, "should return at least 2 parts"),
    )

    # 4. Downtime cost
    cost_data = check(
        "[4] downtime_cost_calculator",
        downtime_cost_calculator(ASSET),
        (lambda d: d["daily_downtime_cost_usd"] == 180_000, "should be $180k/day"),
        (lambda d: len(d["production_orders_at_risk"]) == 3, "should have 3 orders at risk"),
    )

    print("\n  ── Analytics tools ─────────────────────────────")

    # 5. Anomaly detection
    anom = check(
        "[5] anomaly_detector",
        anomaly_detector(ASSET, vib, temp_dev, current),
        (lambda d: d["anomaly_detected"] is True, "anomaly should be detected"),
        (lambda d: d["severity_score"] > 0.25, "severity should be > 0.25"),
    )
    severity = anom.get("severity_score", 0.4)
    signals  = anom.get("contributing_signals", [])

    # 6. RUL prediction
    rul = check(
        "[6] rul_predictor",
        rul_predictor(ASSET, vib, days_ago, avg_life),
        (lambda d: d["rul_hours"] > 0, "RUL should be > 0"),
        (lambda d: d["urgency"] in ("IMMEDIATE","URGENT","PLAN_THIS_WEEK"), "should be urgent"),
    )
    rul_hours     = rul.get("rul_hours", 44)
    life_consumed = rul.get("life_consumed_pct", 96.3)

    # 7. Health score
    health = check(
        "[7] asset_health_scorer",
        asset_health_scorer(ASSET, severity, rul_hours, life_consumed),
        (lambda d: 0 <= d["health_score"] <= 100, "health score should be 0–100"),
        (lambda d: d["status"] in ("AT_RISK","CRITICAL"), "should be AT_RISK or CRITICAL"),
    )
    health_score = health.get("health_score", 29)
    risk_status  = health.get("status", "AT_RISK")

    # 8. Root cause
    rca = check(
        "[8] root_cause_analyzer",
        root_cause_analyzer(ASSET, signals, pattern),
        (lambda d: d["confidence"] > 0.5, "confidence should be > 0.5"),
        (lambda d: "bearing" in d["recommended_fix"].lower(), "fix should mention bearing"),
    )

    print("\n  ── Action tools ────────────────────────────────")

    # 9. Policy — APPROVED action
    check(
        "[9a] policy_validator — DRAFT_WORK_ORDER (expect APPROVED)",
        policy_validator("DRAFT_WORK_ORDER", ASSET, 2_800, False),
        (lambda d: d["decision"] == "APPROVED", "draft WO should be approved"),
    )

    # 10. Policy — shutdown (REQUIRES_APPROVAL)
    check(
        "[9b] policy_validator — MACHINE_SHUTDOWN (expect REQUIRES_APPROVAL)",
        policy_validator("MACHINE_SHUTDOWN", ASSET, 2_800, True),
        (lambda d: d["decision"] == "REQUIRES_APPROVAL", "shutdown needs approval"),
    )

    # 11. Policy — LOTO (REJECTED)
    check(
        "[9c] policy_validator — LOTO_OVERRIDE (expect REJECTED)",
        policy_validator("LOTO_OVERRIDE", ASSET),
        (lambda d: d["decision"] == "REJECTED", "LOTO override must be rejected"),
    )

    # 12. Work order draft
    wo = check(
        "[10] work_order_generator",
        work_order_generator(
            ASSET,
            "Spindle bearing degradation — vibration 0.48g",
            "Replace spindle bearing (SKF 6208) and perform alignment check",
            "CRITICAL",
            estimated_downtime_h=4,
            parts_needed=[
                {"part_number": "SKF-6208-2RS",      "qty": 1, "unit_cost_usd": 87},
                {"part_number": "CASTROL-OPTIEB-5",  "qty": 1, "unit_cost_usd": 45},
            ],
        ),
        (lambda d: d["work_order_id"].startswith("TIT-2026-"), "WO ID should start with TIT-2026-"),
        (lambda d: "DRAFT" in d["status"], "status should be DRAFT"),
    )

    # 13. Notification
    check(
        "[11] notification_service",
        notification_service(
            recipients=["ana.garcia@titan-mfg.com", "plantmanager.valencia@titan-mfg.com"],
            subject="[CRITICAL] CNC-Lathe-07 — Bearing failure predicted",
            body="See work order for details.",
            priority="CRITICAL",
        ),
        (lambda d: d["status"] == "SENT", "notification should be SENT"),
    )

    # 14. Dashboard
    check(
        "[12] dashboard_updater",
        dashboard_updater(ASSET, risk_status, health_score,
                          "Replace spindle bearing within 48h", 0.893),
        (lambda d: d["status"] == "UPDATED", "dashboard should be UPDATED"),
        (lambda d: d["card"]["status_colour"] in ("RED","ORANGE"), "colour should be RED or ORANGE"),
    )

    # ── Final summary ───────────────────────────────────────
    print("\n" + "="*60)
    if errors:
        print(f"  ✗  {len(errors)} tool(s) failed: {', '.join(errors)}")
        print("="*60)
    else:
        print("  ✓  All 12 tools passed — Step 2 complete")
        print("="*60)
        print(f"""
  Key values your agents will work with:
  ─────────────────────────────────────────────────────
  Vibration:      {vib}g  (threshold 0.35g)
  Anomaly score:  {severity}
  RUL:            {rul_hours}h  ({round(rul_hours/24,1)} days) — {rul.get('urgency','')}
  Health score:   {health_score}/100 — {risk_status}
  Daily cost:     $180,000
  Orders at risk: 3  (Airbus due 24 Jun)
  Parts:          IN STOCK
  ─────────────────────────────────────────────────────
  Hand this file to whoever is building Step 3 (agents).
  They import it with:  from step2_mock_tools import *
""")
