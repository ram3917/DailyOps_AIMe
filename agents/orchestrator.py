"""Routing, agent onboarding support, and memory-isolation enforcement.

Loads every registry/*.yaml at startup - adding a new agent means adding a
new registry file and an agents/<name>/agent.py module, never editing this
file. Single-agent routing only for this milestone (no multi-agent merge).
"""
import importlib
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = REPO_ROOT / "registry"


class Orchestrator:
    def __init__(self):
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        registry = {}
        for path in sorted(REGISTRY_DIR.glob("*.yaml")):
            config = yaml.safe_load(path.read_text())
            if config and "name" in config:
                registry[config["name"]] = config
        return registry

    def _agent_module(self, agent_name: str):
        return importlib.import_module(f"agents.{agent_name}.agent")

    def _classify(self, text: str) -> str | None:
        text_lower = text.lower()
        for name, config in self.registry.items():
            keywords = config.get("routing", {}).get("keywords", [name])
            if any(keyword in text_lower for keyword in keywords):
                return name
        return None

    def route_message(self, text: str) -> tuple[str | None, str]:
        """Classify the target agent for an incoming chat message and
        dispatch to it. Returns (agent_name_or_None, reply_text)."""
        target = self._classify(text)
        if target is None:
            return None, "I don't have an agent set up for that yet."
        module = self._agent_module(target)
        return target, module.handle_message(text)

    def ask_agent(self, agent_name: str, question: str) -> str:
        """The ONLY sanctioned cross-agent info path. Invokes the target
        agent in read-only Q&A mode: it queries its own memory and returns
        a natural-language answer only - never raw rows, never write access.
        """
        if agent_name not in self.registry:
            return f"No agent named '{agent_name}' is registered."
        module = self._agent_module(agent_name)
        return module.answer_readonly(question)

    def run_agent_checkin(self, agent_name: str) -> str | None:
        module = self._agent_module(agent_name)
        if hasattr(module, "run_morning_checkin"):
            return module.run_morning_checkin()
        return None

    def run_proactive_checkins(self) -> dict:
        return {name: self.run_agent_checkin(name) for name in self.registry}
