"""Claude API backend for agents whose registry sets backend: claude_api."""
import os
import anthropic

DEFAULT_MODEL = os.environ.get("RAMA_CLAUDE_MODEL", "claude-opus-5")


class ClaudeBackend:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        # Reads ANTHROPIC_API_KEY from the environment - never hardcode a key.
        self.client = anthropic.Anthropic()

    def reply(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
