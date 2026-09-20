from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import AuthorizationError, DomainError, NotFoundError, RT_NS, ValidationError, json_dumps, new_id, now_iso, write_local_artifact
from .db import Database

class AQOOMService:
    def __init__(self, db: Database, storage_root: str | Path):
        self.db = db
        self.storage_root = Path(storage_root)
        self.db.initialize()

    def seed_demo_users(self):
        with self.db.connect() as c:
            for row in [
                ("usr_requester","Requester Demo","REQUESTER"),
                ("usr_executor","Executor Demo","EXECUTOR"),
                ("usr_trainer","Trainer Demo","TRAINER"),
            ]:
                c.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", (*row, now_iso(), "ACTIVE"))

    def _user(self, c, user_id):
        r = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not r: raise NotFoundError(f"Unknown user: {user_id}")
        return dict(r)

    def _role(self, c, user_id, role):
        u = self._user(c, user_id)
        if u["role"] != role: raise AuthorizationError(f"Role {u['role']} cannot perform action requiring {role}")
        return u

    def _trace(self,c,event,entity_type,entity_id,actor,payload=None):
        c.execute("INSERT INTO trace_events VALUES (?,?,?,?,?,?,?)",(new_id("trace"),event,entity_type,entity_id,now_iso(),actor,json_dumps(payload or {})))

    def create_task(self, requester_id, description):
        with self.db.connect() as c:
            self._role(c, requester_id, "REQUESTER")
            if not description or not description.strip(): raise ValidationError("Task description is required")
            task_id = new_id("task")
            c.execute("INSERT INTO tasks VALUES (?,?,?,?,?)",(task_id,requester_id,description.strip(),now_iso(),"CREATED"))
            self._trace(c,"TASK_CREATED","TASK",task_id,requester_id,{"description":description.strip()})
            return self.get_task(task_id)

    def get_task(self, task_id):
        with self.db.connect() as c:
            r=c.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not r: raise NotFoundError(f"Unknown task: {task_id}")
            return dict(r)

    def validate_task(self, requester_id, task_id):
        with self.db.connect() as c:
            self._role(c,requester_id,"REQUESTER")
            r=c.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not r: raise NotFoundError(f"Unknown task: {task_id}")
            if r["requester_id"]!=requester_id: raise AuthorizationError("Only task owner can validate it")
            if r["status"]!="CREATED": raise DomainError("Only CREATED tasks can be validated")
            c.execute("UPDATE tasks SET status='VALIDATED' WHERE task_id=?",(task_id,))
            self._trace(c,"TASK_VALIDATED","TASK",task_id,requester_id)
            return self.get_task(task_id)

    def assign_task(self, requester_id, task_id, executor_id):
        with self.db.connect() as c:
            self._role(c,requester_id,"REQUESTER")
            t=c.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not t: raise NotFoundError(f"Unknown task: {task_id}")
            if t["requester_id"]!=requester_id: raise AuthorizationError("Only task owner can assign it")
            if t["status"]!="VALIDATED": raise DomainError("Task must be VALIDATED before assignment")
            self._role(c,executor_id,"EXECUTOR")
            a=(new_id("assign"),task_id,executor_id,now_iso(),"ASSIGNED")
            c.execute("INSERT INTO assignments VALUES (?,?,?,?,?)",a)
            c.execute("UPDATE tasks SET status='ASSIGNED' WHERE task_id=?",(task_id,))
            self._trace(c,"TASK_ASSIGNED","TASK",task_id,requester_id,{"executor_id":executor_id,"assignment_id":a[0]})
            return dict(c.execute("SELECT * FROM assignments WHERE assignment_id=?",(a[0],)).fetchone())

    def start_execution(self, executor_id, task_id):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            a=c.execute("SELECT * FROM assignments WHERE task_id=?",(task_id,)).fetchone()
            if not a: raise DomainError("No assignment exists")
            if a["executor_id"]!=executor_id: raise AuthorizationError("Only assigned executor can start")
            t=c.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if t["status"]!="ASSIGNED": raise DomainError("Task must be ASSIGNED")
            ex=(new_id("exec"),task_id,executor_id,now_iso(),None,"IN_EXECUTION")
            c.execute("INSERT INTO executions VALUES (?,?,?,?,?,?)",ex)
            c.execute("UPDATE tasks SET status='IN_EXECUTION' WHERE task_id=?",(task_id,))
            self._trace(c,"EXECUTION_STARTED","EXECUTION",ex[0],executor_id,{"task_id":task_id})
            return dict(c.execute("SELECT * FROM executions WHERE execution_id=?",(ex[0],)).fetchone())

    def submit_result(self, executor_id, execution_id, result_status, result_data):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            if e["executor_id"]!=executor_id: raise AuthorizationError("Only assigned executor can submit result")
            if e["status"]!="IN_EXECUTION": raise DomainError("Execution must be IN_EXECUTION")
            if result_status not in {"SUCCESS","FAILED","INCOMPLETE","REJECTED"}: raise ValidationError("Invalid result status")
            if not result_data or not result_data.strip(): raise ValidationError("result_data is required")
            rid=new_id("result")
            c.execute("INSERT INTO results VALUES (?,?,?,?,?)",(rid,execution_id,result_status,result_data,now_iso()))
            self._trace(c,"RESULT_SUBMITTED","RESULT",rid,executor_id,{"execution_id":execution_id,"result_status":result_status})
            return dict(c.execute("SELECT * FROM results WHERE result_id=?",(rid,)).fetchone())

    def submit_evidence(self, executor_id, execution_id, evidence_type, evidence_text):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            r=c.execute("SELECT * FROM results WHERE execution_id=?",(execution_id,)).fetchone()
            if not e or not r: raise DomainError("Evidence requires Execution and Result")
            if e["executor_id"]!=executor_id: raise AuthorizationError("Only assigned executor can submit evidence")
            if e["status"]!="IN_EXECUTION": raise DomainError("Evidence requires active execution")
            if not evidence_text.strip(): raise ValidationError("evidence_text is required")
            evid=new_id("evid")
            ref=write_local_artifact(self.storage_root,execution_id,evid,evidence_text)
            c.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?,?)",(evid,execution_id,r["result_id"],evidence_type or "TEXT",ref,now_iso(),"SUBMITTED"))
            self._trace(c,"EVIDENCE_SUBMITTED","EVIDENCE",evid,executor_id,{"execution_id":execution_id,"result_id":r["result_id"]})
            return dict(c.execute("SELECT * FROM evidence WHERE evidence_id=?",(evid,)).fetchone())

    def validate_evidence(self, requester_id, evidence_id):
        with self.db.connect() as c:
            self._role(c,requester_id,"REQUESTER")
            ev=c.execute("SELECT e.*,t.requester_id FROM evidence e JOIN executions x ON e.execution_id=x.execution_id JOIN tasks t ON x.task_id=t.task_id WHERE e.evidence_id=?",(evidence_id,)).fetchone()
            if not ev: raise NotFoundError(f"Unknown evidence: {evidence_id}")
            if ev["requester_id"]!=requester_id: raise AuthorizationError("Only task owner can validate evidence")
            c.execute("UPDATE evidence SET status='VALIDATED' WHERE evidence_id=?",(evidence_id,))
            self._trace(c,"EVIDENCE_VALIDATED","EVIDENCE",evidence_id,requester_id)
            return dict(c.execute("SELECT * FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone())

    def complete_execution(self, executor_id, execution_id):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            r=c.execute("SELECT * FROM results WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            if e["executor_id"]!=executor_id: raise AuthorizationError("Only assigned executor can complete")
            if e["status"]!="IN_EXECUTION": raise DomainError("Execution must be IN_EXECUTION")
            if not r: raise DomainError("Completion requires Result")
            c.execute("UPDATE executions SET status='COMPLETED',finished_at=? WHERE execution_id=?",(now_iso(),execution_id))
            c.execute("UPDATE tasks SET status='COMPLETED' WHERE task_id=?",(e["task_id"],))
            self._trace(c,"EXECUTION_FINISHED","EXECUTION",execution_id,executor_id,{"status":"COMPLETED"})
            return dict(c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone())

    def fail_execution(self, executor_id, execution_id, reason):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            if e["status"]!="IN_EXECUTION": raise DomainError("Only active execution can fail")
            c.execute("UPDATE executions SET status='FAILED',finished_at=? WHERE execution_id=?",(now_iso(),execution_id))
            c.execute("UPDATE tasks SET status='FAILED' WHERE task_id=?",(e["task_id"],))
            self._trace(c,"EXECUTION_FAILED","EXECUTION",execution_id,executor_id,{"reason":reason})
            return dict(c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone())

    def record_effort(self, executor_id, execution_id, t_accounted_ns):
        with self.db.connect() as c:
            self._role(c,executor_id,"EXECUTOR")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            if e["executor_id"]!=executor_id: raise AuthorizationError("Only assigned executor can record effort")
            if e["status"]!="COMPLETED": raise DomainError("Effort requires COMPLETED execution")
            if not isinstance(t_accounted_ns,int) or t_accounted_ns<=0: raise ValidationError("T_accounted_ns must be positive integer")
            eff=(new_id("effort"),execution_id,t_accounted_ns,"RT = T_accounted_ns / 30ns; MVP does not infer T_accounted",now_iso(),"ACCOUNTED")
            c.execute("INSERT INTO effort_records VALUES (?,?,?,?,?,?)",eff)
            self._trace(c,"EFFORT_RECORDED","EFFORT",eff[0],executor_id,{"execution_id":execution_id,"t_accounted_ns":t_accounted_ns})
            return dict(c.execute("SELECT * FROM effort_records WHERE effort_id=?",(eff[0],)).fetchone())

    def calculate_rt(self, execution_id):
        with self.db.connect() as c:
            eff=c.execute("SELECT * FROM effort_records WHERE execution_id=?",(execution_id,)).fetchone()
            if not eff: raise ValidationError("T_accounted is missing")
            existing=c.execute("SELECT * FROM rt_records WHERE execution_id=?",(execution_id,)).fetchone()
            if existing: return dict(existing)
            rt=(new_id("rt"),execution_id,eff["effort_id"],eff["t_accounted_ns"],eff["t_accounted_ns"]/RT_NS,"1 RT = 30 ns; RT = T_accounted_ns / 30",now_iso())
            c.execute("INSERT INTO rt_records VALUES (?,?,?,?,?,?,?)",rt)
            self._trace(c,"RT_CALCULATED","RT",rt[0],None,{"execution_id":execution_id,"rt_value":rt[4]})
            return dict(c.execute("SELECT * FROM rt_records WHERE rt_record_id=?",(rt[0],)).fetchone())

    def create_settlement(self, requester_id, execution_id):
        with self.db.connect() as c:
            self._role(c,requester_id,"REQUESTER")
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            t=c.execute("SELECT * FROM tasks WHERE task_id=?",(e["task_id"],)).fetchone()
            if t["requester_id"]!=requester_id: raise AuthorizationError("Only task owner can create settlement")
            r=c.execute("SELECT * FROM results WHERE execution_id=?",(execution_id,)).fetchone()
            ev=c.execute("SELECT * FROM evidence WHERE execution_id=? AND status='VALIDATED'",(execution_id,)).fetchone()
            rt=c.execute("SELECT * FROM rt_records WHERE execution_id=?",(execution_id,)).fetchone()
            if e["status"]!="COMPLETED" or not r or not ev or not rt: raise DomainError("Settlement requires completed execution, result, validated evidence, and valid RT")
            s=(new_id("settle"),t["task_id"],execution_id,rt["rt_record_id"],rt["rt_value"],"RECORDED",now_iso())
            c.execute("INSERT INTO settlement_records VALUES (?,?,?,?,?,?,?)",s)
            self._trace(c,"SETTLEMENT_RECORDED","SETTLEMENT",s[0],requester_id,{"execution_id":execution_id,"rt_record_id":rt["rt_record_id"]})
            return dict(c.execute("SELECT * FROM settlement_records WHERE settlement_id=?",(s[0],)).fetchone())

    def create_training_record(self, execution_id):
        with self.db.connect() as c:
            r=c.execute("SELECT * FROM results WHERE execution_id=?",(execution_id,)).fetchone()
            if not r: raise DomainError("Training record requires Result")
            existing=c.execute("SELECT * FROM training_records WHERE execution_id=?",(execution_id,)).fetchone()
            if existing: return dict(existing)
            tr=(new_id("train"),execution_id,r["result_id"],json_dumps({"execution_id":execution_id,"result_id":r["result_id"],"scope":"MVP_EXECUTION_DATA"}),now_iso(),"RECORDED")
            c.execute("INSERT INTO training_records VALUES (?,?,?,?,?,?)",tr)
            self._trace(c,"TRAINING_RECORDED","TRAINING",tr[0],None,{"execution_id":execution_id})
            return dict(c.execute("SELECT * FROM training_records WHERE training_record_id=?",(tr[0],)).fetchone())

    def get_training_data(self, trainer_id):
        with self.db.connect() as c:
            self._role(c,trainer_id,"TRAINER")
            return [dict(r) for r in c.execute("SELECT * FROM training_records ORDER BY created_at").fetchall()]

    def get_trace(self, execution_id):
        with self.db.connect() as c:
            rows=c.execute("SELECT * FROM trace_events ORDER BY timestamp").fetchall()
            out=[]
            for r in rows:
                payload=__import__("json").loads(r["payload"])
                if r["entity_id"]==execution_id or payload.get("execution_id")==execution_id:
                    d=dict(r); d["payload"]=payload; out.append(d)
            return out

    def get_execution_bundle(self, execution_id):
        with self.db.connect() as c:
            e=c.execute("SELECT * FROM executions WHERE execution_id=?",(execution_id,)).fetchone()
            if not e: raise NotFoundError(f"Unknown execution: {execution_id}")
            task=c.execute("SELECT * FROM tasks WHERE task_id=?",(e["task_id"],)).fetchone()
            assignment=c.execute("SELECT * FROM assignments WHERE task_id=?",(e["task_id"],)).fetchone()
            result=c.execute("SELECT * FROM results WHERE execution_id=?",(execution_id,)).fetchone()
            evidence=c.execute("SELECT * FROM evidence WHERE execution_id=? ORDER BY created_at",(execution_id,)).fetchall()
            effort=c.execute("SELECT * FROM effort_records WHERE execution_id=?",(execution_id,)).fetchone()
            rt=c.execute("SELECT * FROM rt_records WHERE execution_id=?",(execution_id,)).fetchone()
            settlement=c.execute("SELECT * FROM settlement_records WHERE execution_id=?",(execution_id,)).fetchone()
            training=c.execute("SELECT * FROM training_records WHERE execution_id=?",(execution_id,)).fetchone()
            return {"task":dict(task),"assignment":dict(assignment) if assignment else None,"execution":dict(e),"result":dict(result) if result else None,"evidence":[dict(x) for x in evidence],"effort":dict(effort) if effort else None,"rt":dict(rt) if rt else None,"settlement":dict(settlement) if settlement else None,"training":dict(training) if training else None,"trace":self.get_trace(execution_id)}
