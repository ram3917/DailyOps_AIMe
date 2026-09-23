"""Onboarding flow for an agent: scope interview, then context interview.

CLI-driven for this milestone (run: python onboarding/onboard_agent.py
personal_trainer). run_onboarding() takes an injectable ask_fn so the same
flow can later be driven by a Telegram conversation instead of input() -
that's the extension point; a real multi-turn Telegram onboarding UI is
out of scope for this milestone.

Output:
- Updates registry/<agent>.yaml (currently just `backend`; the rest of an
  agent's registry is static config checked into the repo)
- Creates memory/<agent>.db if it doesn't exist, applying schema.sql
- Writes context-interview answers into that agent's own profile table
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from memory.db import open_agent_db, set_profile

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = REPO_ROOT / "registry"

SCOPE_QUESTIONS = [
    ("primary_goal", "Primary goal (general fitness / weight target / event training / injury recovery)?"),
    ("tone", "Preferred tone (e.g. blunt, encouraging, clinical)?"),
]

CONTEXT_QUESTION_TEXT = {
    "daily_step_goal": "Daily step goal?",
    "sleep_target_hours": "Sleep target, in hours?",
    "injury_history_or_limits": "Any injuries or movement limits I should always factor in?",
    "preferred_workout_types": "Preferred workout types?",
    "morning_checkin_time": "What time should the morning check-in run (HH:MM, 24h, your local time)?",
}

BACKEND_CHOICES = {"1": "claude_api", "2": "local_model"}


def load_registry(agent_name: str) -> dict:
    path = REGISTRY_DIR / f"{agent_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No registry template at {path}. This milestone ships "
            f"registry/personal_trainer.yaml; add a template for other "
            f"agents (tools, onboarding_questions, proactive_checkins) "
            f"before onboarding them."
        )
    return yaml.safe_load(path.read_text())


def save_registry(agent_name: str, config: dict) -> None:
    path = REGISTRY_DIR / f"{agent_name}.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False))


def run_onboarding(agent_name: str, ask_fn) -> None:
    """ask_fn(question: str) -> str"""
    config = load_registry(agent_name)

    scope_answers = {key: ask_fn(question) for key, question in SCOPE_QUESTIONS}

    backend_choice = ask_fn(
        "Which backend? 1) Claude API  2) Local model (stub only right now) [1]"
    ).strip()
    config["backend"] = BACKEND_CHOICES.get(backend_choice, "claude_api")
    save_registry(agent_name, config)

    conn = open_agent_db(agent_name)
    set_profile(conn, "primary_goal", scope_answers["primary_goal"])
    set_profile(conn, "tone", scope_answers["tone"])

    context_keys = config.get("onboarding_questions", {}).get("context", [])
    for key in context_keys:
        question = CONTEXT_QUESTION_TEXT.get(key, f"{key}?")
        set_profile(conn, key, ask_fn(question))
    conn.close()

    print(
        f"\n{agent_name} onboarded.\n"
        f"  registry: registry/{agent_name}.yaml (backend={config['backend']})\n"
        f"  memory:   memory/{agent_name}.db"
    )


def cli_ask(question: str) -> str:
    return input(f"{question}\n> ").strip()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python onboarding/onboard_agent.py <agent_name>")
        sys.exit(1)
    run_onboarding(sys.argv[1], cli_ask)


if __name__ == "__main__":
    main()
