# core/openstack_manager.py
import os
import json
import requests
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://172.17.99.132:30090/query")

class OpenstackManager:
    """
    Minimal manager for OpenStack MCP:
      - reads stored logs forwarded by Fluent Bit
      - queries Prometheus for node/service metrics
      - simple actions (restart systemd service on a node via SSH placeholder)
      - analysis combining logs/events/metrics
    """

    def __init__(self, logs_dir: str = "/var/lib/mcp-openstack/logs"):
        # Fluent Bit forwards logs to MCP which writes JSON logs into files under logs_dir
        self.logs_dir = logs_dir
        os.makedirs(self.logs_dir, exist_ok=True)

    # ------------ logs ingestion (Fluent Bit will POST to MCP, handler writes files) ------------
    def save_log_record(self, record: Dict[str, Any]):
        """
        Write one JSON log line to file per node or service.
        Example record keys: timestamp, node, service, level, message
        """
        node = record.get("node", "unknown")
        fname = os.path.join(self.logs_dir, f"{node}.jsonl")
        with open(fname, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return {"status": "ok", "file": fname}

    def read_logs(self, node: Optional[str] = None, service: Optional[str] = None, tail: int = 500):
        """
        Return last `tail` log lines optionally filtered by node/service.
        """
        results = []
        files = []
        if node:
            path = os.path.join(self.logs_dir, f"{node}.jsonl")
            if os.path.exists(path):
                files = [path]
        else:
            files = [os.path.join(self.logs_dir, f) for f in os.listdir(self.logs_dir) if f.endswith(".jsonl")]

        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    lines = fh.readlines()[-tail:]
                    for ln in lines:
                        try:
                            obj = json.loads(ln)
                        except:
                            continue
                        if service and obj.get("service") != service:
                            continue
                        results.append(obj)
            except Exception:
                continue

        # sort by timestamp if present
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return results[:tail]

    # ------------ Prometheus metric helpers ------------
    def _prometheus_query(self, query: str, timeout: int = 10):
        r = requests.get(PROMETHEUS_URL, params={"query": query}, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def get_service_cpu(self, service_name: str, window_seconds: int = 60):
        # a generic container/node metric example; adjust labels per your Prometheus metrics
        query = f'rate(process_cpu_seconds_total{{service="{service_name}"}}[1m])'
        try:
            resp = self._prometheus_query(query)
            return resp.get("data", {}).get("result", [])
        except Exception as e:
            raise

    def get_node_cpu_usage(self, node: str):
        query = f'instance:node_cpu:rate:sum{{instance="{node}"}}'  # placeholder; adapt to your metrics
        resp = self._prometheus_query(query)
        return resp.get("data", {}).get("result", [])

    def get_service_memory(self, service_name: str):
        query = f'process_resident_memory_bytes{{service="{service_name}"}}'
        resp = self._prometheus_query(query)
        return resp.get("data", {}).get("result", [])

    # ------------ Events (placeholder) ------------
    def list_events(self, namespace: Optional[str] = None):
        # OpenStack events not standardized — you may read from message bus or from logs
        # For now return filtered log-level "EVENT" items
        events = []
        recs = self.read_logs()
        for r in recs:
            if r.get("level", "").upper() in ("WARN", "ERROR", "CRITICAL", "EVENT"):
                events.append(r)
        return events

    # ------------ Actions (placeholders) ------------
    def restart_service_on_node(self, node: str, service: str, ssh_user: str = "root", ssh_key: Optional[str] = None):
        """
        Example placeholder: runs ssh node 'systemctl restart <service>'
        In production you should implement secure remote command execution (Ansible, Salt, SSH Keys).
        """
        cmd = f"ssh {ssh_user}@{node} sudo systemctl restart {service}"
        try:
            out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30, text=True)
            return {"ok": True, "output": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------ Analyze service (logs + events + metrics) ------------
    def analyze_service(self, node: str, service: str):
        analysis = {}
        # 1. recent logs
        logs = self.read_logs(node=node, service=service, tail=300)
        analysis["logs_sample"] = logs[:200]

        # 2. events (from logs)
        events = [l for l in logs if l.get("level", "").upper() in ("ERROR", "CRITICAL", "WARN", "EVENT")]
        analysis["events"] = events[:50]

        # 3. metrics
        try:
            cpu = self.get_service_cpu(service)
            mem = self.get_service_memory(service)
            analysis["metrics"] = {"cpu": cpu, "memory": mem}
        except Exception as e:
            analysis["metrics_error"] = str(e)

        # 4. heuristics: simple rules to detect issues
        heuristics = []
        # CrashLoop-ish: many "restart" messages or frequent ERROR lines
        err_count = sum(1 for l in logs if "error" in (l.get("message") or "").lower())
        if err_count > 20:
            heuristics.append("High error rate in logs (>=20 recent error lines) — risk of instability")

        # OOM-like detection from logs
        if any("oom" in (l.get("message") or "").lower() for l in logs):
            heuristics.append("OOM indications in logs — memory pressure possible")

        # CPU spike detection: if Prometheus returned data with high values
        try:
            if cpu and isinstance(cpu, list) and len(cpu) > 0:
                # simplistic check: pick first sample value and check numeric value
                sample = cpu[0].get("value", [None, "0"])[1]
                try:
                    val = float(sample)
                    if val > 0.5:
                        heuristics.append(f"High CPU (rate ~ {val})")
                except:
                    pass
        except:
            pass

        analysis["heuristics"] = heuristics

        # 5. recommended actions
        recs = []
        if "OOM" in " ".join(heuristics).upper() or any("oom" in (l.get("message") or "").lower() for l in logs):
            recs.append({"action": "increase_memory", "reason": "OOM signals in logs"})
            recs.append({"action": "restart_service", "service": service})
        elif err_count > 20:
            recs.append({"action": "restart_service", "service": service})
            recs.append({"action": "collect_more_logs", "reason": "high error rate"})

        analysis["recommendations"] = recs
        return analysis
