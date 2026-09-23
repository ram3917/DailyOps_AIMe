"""Dispatches to the right model backend per agent, based on that agent's
registry `backend` field. Agents call get_backend(agent_name) and never
instantiate a backend class directly - that's what makes backend swappable
per agent via a registry edit alone.
"""
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = REPO_ROOT / "registry"

_backend_cache = {}


def _agent_backend_name(agent_name: str) -> str:
    path = REGISTRY_DIR / f"{agent_name}.yaml"
    if not path.exists():
        return "claude_api"
    config = yaml.safe_load(path.read_text()) or {}
    return config.get("backend", "claude_api")


def get_backend(agent_name: str):
    backend_name = _agent_backend_name(agent_name)
    if backend_name not in _backend_cache:
        if backend_name == "local_model":
            from models.local_backend import LocalBackend
            _backend_cache[backend_name] = LocalBackend()
        else:
            from models.claude_backend import ClaudeBackend
            _backend_cache[backend_name] = ClaudeBackend()
    return _backend_cache[backend_name]
