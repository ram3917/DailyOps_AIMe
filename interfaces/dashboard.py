"""Minimal localhost-only dashboard stub: read-only view of agent state.

Deliberately binds to 127.0.0.1 only - no 0.0.0.0, no tunneling, no public
hosting. Not required for this milestone's acceptance criteria; this is
the extension point the spec asks for, not a finished UI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify

from agents.orchestrator import Orchestrator
from memory.db import get_all_profile, open_agent_db

app = Flask(__name__)
orchestrator = Orchestrator()


@app.route("/")
def index():
    agents = {}
    for name in orchestrator.registry:
        conn = open_agent_db(name)
        agents[name] = get_all_profile(conn)
        conn.close()
    return jsonify({"agents": agents})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5151, debug=False)
