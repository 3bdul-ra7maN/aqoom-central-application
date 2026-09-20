from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .core import DomainError
from .services import AQOOMService

def body(h):
    n=int(h.headers.get("Content-Length","0"))
    return json.loads(h.rfile.read(n).decode("utf-8")) if n else {}

class Handler(BaseHTTPRequestHandler):
    service: AQOOMService | None = None

    def send_json(self,payload,status=200):
        data=json.dumps(payload,ensure_ascii=False,indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def actor(self): return self.headers.get("X-User-ID","")

    def do_GET(self):
        try:
            path=urlparse(self.path).path
            if path=="/health": return self.send_json({"status":"OK","product":"AQOOM Central Application MVP"})
            if path=="/training": return self.send_json(self.service.get_training_data(self.actor()))
            parts=[p for p in path.split("/") if p]
            if len(parts)==2 and parts[0]=="tasks": return self.send_json(self.service.get_task(parts[1]))
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="trace": return self.send_json(self.service.get_execution_bundle(parts[1]))
            if path=="/": return self.send_json({"product":"AQOOM Central Application MVP","ui":"Use the React/Vite app at repository root."})
            raise DomainError("Not found")
        except Exception as exc: self.error(exc)

    def do_POST(self):
        try:
            path=urlparse(self.path).path
            parts=[p for p in path.split("/") if p]
            data=body(self); actor=self.actor()
            if path=="/tasks": return self.send_json(self.service.create_task(actor,data.get("description","")),201)
            if len(parts)==3 and parts[0]=="tasks" and parts[2]=="validate": return self.send_json(self.service.validate_task(actor,parts[1]))
            if len(parts)==3 and parts[0]=="tasks" and parts[2]=="assign": return self.send_json(self.service.assign_task(actor,parts[1],data["executor_id"]))
            if path=="/executions/start": return self.send_json(self.service.start_execution(actor,data["task_id"]),201)
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="result": return self.send_json(self.service.submit_result(actor,parts[1],data["result_status"],data["result_data"]),201)
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="evidence": return self.send_json(self.service.submit_evidence(actor,parts[1],data["evidence_type"],data["evidence_text"]),201)
            if len(parts)==3 and parts[0]=="evidence" and parts[2]=="validate": return self.send_json(self.service.validate_evidence(actor,parts[1]))
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="complete": return self.send_json(self.service.complete_execution(actor,parts[1]))
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="fail": return self.send_json(self.service.fail_execution(actor,parts[1],data.get("reason","")))
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="effort": return self.send_json(self.service.record_effort(actor,parts[1],int(data["t_accounted_ns"])),201)
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="rt": return self.send_json(self.service.calculate_rt(parts[1]),201)
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="settlement": return self.send_json(self.service.create_settlement(actor,parts[1]),201)
            if len(parts)==3 and parts[0]=="executions" and parts[2]=="training": return self.send_json(self.service.create_training_record(parts[1]),201)
            raise DomainError("Not found")
        except Exception as exc: self.error(exc)

    def error(self,exc):
        status=exc.status_code if isinstance(exc,DomainError) else 500
        self.send_json({"error":type(exc).__name__,"message":str(exc)},status)

    def log_message(self,*args): pass

def serve(service,host="127.0.0.1",port=8000):
    Handler.service=service
    ThreadingHTTPServer((host,port),Handler).serve_forever()
