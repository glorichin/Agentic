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

### Step 3 — The agent crew (`titan_agents.py`)

This is the engine that unites everything: it loads the LLM (Step 1 style),
wraps the 12 mock tools (Step 2) as CrewAI tools, and defines the 5 agents
from the *Agent Prompts* deliverable. It exposes one function:

```python
from titan_agents import run_pipeline, DEMO_EVENT

result = run_pipeline(DEMO_EVENT)
print(result["final"])          # orchestrator's final decision (dict)
print(result["agents"]["cost"]) # any specialist's assessment
```

The crew runs as a **sequential pipeline** — the four specialists assess the
event, the Safety & Governance agent gates the proposed actions, and the
Orchestrator synthesizes everything (conflict check → priority score →
AUTONOMOUS vs ESCALATE). Run it directly to test:

```bash
python3 titan_agents.py
```

### Step 4 — The Streamlit demo (`app.py`)

The visual demo. Pick a trigger event in the sidebar, click **Run the crew**,
and watch each agent's assessment appear live, followed by the Orchestrator's
final decision.

```bash
pip install -r requirements.txt   # includes streamlit
# make sure your key is in .env
streamlit run app.py
```

### Colab path (`titan_maintenance_crew.ipynb`)

Same engine, runnable in Google Colab — clone the repo, paste your key when
prompted (via `getpass`, so it's never saved), and run all cells.

## File structure

```
titan_mip/
├── .env                          ← your Gemini key (never commit this)
├── .gitignore
├── requirements.txt
├── step1_setup.py                ← run first — checks packages + API key
├── step2_mock_tools.py           ← all 12 mock tools + smoke test
├── titan_agents.py               ← Step 3 — the 5 agents + run_pipeline()
├── app.py                        ← Step 4 — Streamlit demo
├── titan_maintenance_crew.ipynb  ← Colab notebook (same engine)
└── README.md
```
