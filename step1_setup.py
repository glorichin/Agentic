"""
step1_setup.py — Titan MIP Environment Setup & Verification
─────────────────────────────────────────────────────────────
Run this first to confirm your Gemini API key works and all
packages are installed correctly before your teammates build
the agents in Step 3.

Usage:
    python3 step1_setup.py
"""

import sys
import os

# Windows consoles default to a codepage that can't render the ✓/✗/⚠
# symbols below — force UTF-8 so this script runs unmodified everywhere.
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── 1. Check Python version ────────────────────────────────
print("\n" + "="*60)
print("  TITAN MIP — Step 1: Environment Check")
print("="*60)

major, minor = sys.version_info[:2]
if major < 3 or minor < 10:
    print(f"\n✗  Python {major}.{minor} found — need 3.10 or higher.")
    print("   Download from https://python.org")
    sys.exit(1)
print(f"\n✓  Python {major}.{minor}")

# ── 2. Check required packages ─────────────────────────────
required = {
    "crewai":       "crewai",
    "google.genai": "google-genai",
    "dotenv":       "python-dotenv",
}

all_ok = True
for module, package in required.items():
    try:
        __import__(module)
        # get version where possible
        try:
            import importlib.metadata
            ver = importlib.metadata.version(package)
            print(f"✓  {package} ({ver})")
        except Exception:
            print(f"✓  {package}")
    except ImportError:
        print(f"✗  {package} not found — run:  pip install {package}")
        all_ok = False

if not all_ok:
    print("\n  Fix the missing packages above, then re-run this script.")
    sys.exit(1)

# ── 3. Load .env ───────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY", "").strip()

if not api_key:
    print("\n✗  GEMINI_API_KEY not set.")
    print("   1. Copy .env.example to .env")
    print("   2. Paste your key from https://aistudio.google.com/apikey")
    sys.exit(1)

if not api_key.startswith("AI"):
    print(f"\n⚠  Key looks unusual (doesn't start with 'AI'): {api_key[:8]}...")
    print("   Double-check you copied the full key from AI Studio.")

print(f"\n✓  GEMINI_API_KEY loaded ({api_key[:8]}...)")

# ── 4. Live API test ───────────────────────────────────────
print("\n  Testing Gemini API connection...")

try:
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Reply with exactly: TITAN_MIP_OK",
    )
    reply = response.text.strip()

    if "TITAN_MIP_OK" in reply:
        print("✓  Gemini API live — model responding correctly")
    else:
        print(f"⚠  Unexpected reply: {reply!r}")
        print("   API is working but response was unexpected — probably fine.")

except Exception as e:
    print(f"✗  API call failed: {e}")
    print("   Check your key at https://aistudio.google.com/apikey")
    sys.exit(1)

# ── 5. Test CrewAI LLM wrapper ────────────────────────────
print("\n  Testing CrewAI LLM wrapper with Gemini...")

try:
    from crewai import LLM

    llm = LLM(
        model="gemini/gemini-2.0-flash",
        api_key=api_key,
        temperature=0.1,   # low temp = more reliable structured output
    )
    print("✓  CrewAI LLM wrapper ready")
    print(f"   Model: gemini/gemini-2.0-flash")
    print(f"   Temperature: 0.1 (consistent structured output)")

except Exception as e:
    print(f"✗  CrewAI LLM setup failed: {e}")
    sys.exit(1)

# ── 6. Summary ─────────────────────────────────────────────
print("\n" + "="*60)
print("  ✓  Step 1 complete — environment ready")
print("="*60)
print("""
  Next steps:
  ─────────────────────────────────────────────────────
  Run Step 2:   python3 step2_mock_tools.py
  (your teammates need this for Step 3 — CrewAI agents)
""")
