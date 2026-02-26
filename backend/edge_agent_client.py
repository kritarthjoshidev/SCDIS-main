"""
Simple local edge agent client.

Usage:
  python backend/edge_agent_client.py --base-url http://127.0.0.1:8010 --edge-id edge-lab-01
"""

from __future__ import annotations

import argparse
import json
import platform
import socket
from datetime import datetime
from urllib import request


def _collect_payload(edge_id: str) -> dict:
    return {
        "edge_id": edge_id,
        "timestamp": datetime.utcnow().isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "disk_percent": 0.0,
        "battery_percent": None,
        "power_plugged": None,
        "process_count": 0,
        "network_type": "unknown",
        "source": "edge-agent-script",
    }


def main():
    parser = argparse.ArgumentParser(description="Push local edge telemetry to SCDIS backend")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--edge-id", default="edge-local-script")
    args = parser.parse_args()

    payload = _collect_payload(args.edge_id)
    endpoint = f"{args.base_url.rstrip('/')}/monitoring/edge-agent/ingest"
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")

    with request.urlopen(req, timeout=10) as resp:
        print(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
