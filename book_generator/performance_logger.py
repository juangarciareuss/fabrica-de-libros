# book_generator/performance_logger.py
import json
import os
import logging
from datetime import datetime

class PerformanceLogger:
    def __init__(self, workspace_dir):
        self.log_path = os.path.join(workspace_dir, "performance_log.json")
        self.records = []
        self.load()

    def load(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r', encoding='utf-8') as f:
                self.records = json.load(f)

    def save(self):
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, indent=4, ensure_ascii=False)

    def log(self, agent_id, event_type, details):
        """Registra un evento de rendimiento para un agente."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "event": event_type,
            "details": details
        }
        self.records.append(record)
        self.save()
        logging.debug(f"PERFORMANCE LOGGED for {agent_id}: {event_type}")