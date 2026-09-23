"""Stub for a locally-hosted model runtime (e.g. Ollama).

No local runtime is configured for this deployment. Registries should set
backend: claude_api until a real local runtime is wired up here - this
class exists so that swap is a registry edit, not a code change.
"""


class LocalBackend:
    def reply(self, system: str, user_message: str, **kwargs) -> str:
        raise NotImplementedError(
            "No local model backend is configured. Set this agent's registry "
            "`backend` to claude_api, or implement LocalBackend against your "
            "local model runtime."
        )
