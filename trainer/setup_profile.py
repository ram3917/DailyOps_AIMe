"""Interactive profile setup/edit. Run again anytime to update answers.

Run: python -m trainer.setup_profile
"""
from trainer import db

QUESTIONS = [
    ("primary_goal", "Primary goal (general fitness / weight target / event training / injury recovery)?"),
    ("tone", "How should I talk to you? (e.g. blunt, encouraging, no-nonsense)"),
    ("daily_step_goal", "Daily step goal?"),
    ("sleep_target_hours", "Sleep target, in hours?"),
    ("injury_history_or_limits", "Any injuries or movement limits I should always factor in?"),
    ("preferred_workout_types", "Preferred workout types?"),
]


def main() -> None:
    for key, question in QUESTIONS:
        current = db.get_profile(key)
        suffix = f" [{current}]" if current else ""
        answer = input(f"{question}{suffix}\n> ").strip()
        if answer:
            db.set_profile(key, answer)
    print("Profile saved to trainer.db.")


if __name__ == "__main__":
    main()
