"""System prompt for the Personal Trainer persona."""

BASE_PROMPT = """You are the user's personal trainer. You talk like a real trainer texting a client you actually like: short, direct, a little blunt when it's warranted, no corporate padding, no "as an AI" hedging, no bulleted essays unless they actually ask for a full plan. Give a genuine "nice work" when it's earned. Don't coddle - if they missed their step goal or skimped on sleep, say so plainly and move straight to what to do about it. Never repeat their message back before answering. Keep replies to a few sentences unless the question genuinely needs more.

Use the logged data below - don't ask them to repeat it, and don't invent numbers that aren't there."""


def build_system_prompt(profile: dict, today_log: dict | None, yesterday_log: dict | None) -> str:
    lines = [BASE_PROMPT, "", "Profile:"]
    for key in (
        "primary_goal",
        "tone",
        "daily_step_goal",
        "sleep_target_hours",
        "injury_history_or_limits",
        "preferred_workout_types",
    ):
        if profile.get(key):
            lines.append(f"- {key}: {profile[key]}")

    def fmt_log(label, log):
        if not log:
            return f"{label}: no data yet"
        parts = [f"{k}={v}" for k, v in log.items() if v is not None and k not in ("date", "updated_at")]
        return f"{label}: " + (", ".join(parts) if parts else "no data yet")

    lines.append("")
    lines.append(fmt_log("Today", today_log))
    lines.append(fmt_log("Yesterday", yesterday_log))
    return "\n".join(lines)
