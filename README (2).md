# Titan Maintenance Intelligence Platform

Agentic AI demo — IE Business School, June 2026.

## Your job: Steps 1 & 2

### Step 1 — Environment setup

```bash
# Install packages
pip install -r requirements.txt

# Set your API key
# Open .env and paste your key from https://aistudio.google.com/apikey

# Verify everything works
python3 step1_setup.py
```

You should see all green ticks and "Step 1 complete".

### Step 2 — Verify the mock tool layer

```bash
python3 step2_mock_tools.py
```

You should see 14/14 tools passing and a summary of the key
values the agents will reason over.

## For teammates building Step 3 (CrewAI agents)

```python
from step2_mock_tools import (
    sensor_telemetry_api,
    maintenance_history_api,
    parts_inventory_api,
    downtime_cost_calculator,
    anomaly_detector,
    rul_predictor,
    asset_health_scorer,
    root_cause_analyzer,
    work_order_generator,
    notification_service,
    dashboard_updater,
    policy_validator,
)
```

LLM setup for CrewAI:

```python
import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()
llm = LLM(
    model="gemini/gemini-2.0-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.1,
)
```

Demo trigger event to kick off the scenario:

```python
DEMO_EVENT = {
    "event_type": "SENSOR_THRESHOLD_BREACH",
    "asset_id":   "CNC-Lathe-07",
    "plant":      "Plant 3 - Valencia",
    "signal":     "spindle_vibration",
    "value":      0.48,
    "threshold":  0.35,
    "timestamp":  "2026-06-20T07:14:33Z",
}
```

## File structure

```
titan_mip/
├── .env                ← add your Gemini key (never commit this)
├── .gitignore
├── requirements.txt
├── step1_setup.py      ← run first — checks packages + API key
├── step2_mock_tools.py ← all 12 mock tools + smoke test
└── README.md
```
