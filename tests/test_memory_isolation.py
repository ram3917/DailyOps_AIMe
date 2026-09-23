"""Structural enforcement, not just convention: every agent module may
only open its own memory database, via memory.db.open_agent_db() called
with its own literal agent name.

This is generic across agents/*/*.py, so it stays meaningful as more
agents are onboarded later without needing to change this test.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / "agents"


def _agent_names():
    return [
        p.name
        for p in AGENTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_") and p.name != "__pycache__"
    ]


def _module_level_string_constants(tree: ast.Module) -> dict:
    """NAME = "literal" assignments at module scope, e.g. AGENT_NAME =
    "personal_trainer". Used to resolve open_agent_db(AGENT_NAME) without
    accepting genuinely dynamic arguments."""
    constants = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _open_agent_db_calls(py_file: Path):
    """Yield the resolved string argument of every open_agent_db(...) call
    in this file. Accepts a string literal or a reference to a module-level
    string constant; raises for anything else (a function parameter, an
    f-string, another call's result, ...) since that would defeat static
    verification entirely."""
    tree = ast.parse(py_file.read_text())
    constants = _module_level_string_constants(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open_agent_db"
            and node.args
        ):
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield arg.value
            elif isinstance(arg, ast.Name) and arg.id in constants:
                yield constants[arg.id]
            else:
                raise AssertionError(
                    f"{py_file}: open_agent_db() called with an argument "
                    f"that isn't a string literal or a module-level string "
                    f"constant - can't statically verify memory isolation."
                )


def test_no_agent_module_opens_another_agents_db():
    for agent_name in _agent_names():
        for py_file in (AGENTS_DIR / agent_name).rglob("*.py"):
            for opened_name in _open_agent_db_calls(py_file):
                assert opened_name == agent_name, (
                    f"{py_file} opens '{opened_name}'s database, but belongs "
                    f"to agent '{agent_name}' - cross-agent DB access must go "
                    f"through orchestrator.ask_agent() instead."
                )


def test_agents_never_import_sqlite_directly():
    """Second line of defense: agent code should go through memory.db, not
    open sqlite3 connections itself, which would bypass the check above."""
    for agent_name in _agent_names():
        for py_file in (AGENTS_DIR / agent_name).rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    assert not any(alias.name == "sqlite3" for alias in node.names), (
                        f"{py_file} imports sqlite3 directly - use "
                        f"memory.db.open_agent_db() instead."
                    )
