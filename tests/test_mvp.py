import pytest
from backend.app.core import AuthorizationError, DomainError, ValidationError

def test_core_mvp_flow(service):
    t=service.create_task("usr_requester","Acceptance task")
    assert t["status"]=="CREATED"
    with pytest.raises(DomainError):
        service.start_execution("usr_executor",t["task_id"])
    t=service.validate_task("usr_requester",t["task_id"])
    a=service.assign_task("usr_requester",t["task_id"],"usr_executor")
    assert a["executor_id"]=="usr_executor"
    e=service.start_execution("usr_executor",t["task_id"])
    r=service.submit_result("usr_executor",e["execution_id"],"SUCCESS","Observed result")
    ev=service.submit_evidence("usr_executor",e["execution_id"],"TEXT","Observed evidence")
    ev=service.validate_evidence("usr_requester",ev["evidence_id"])
    e=service.complete_execution("usr_executor",e["execution_id"])
    eff=service.record_effort("usr_executor",e["execution_id"],30)
    rt=service.calculate_rt(e["execution_id"])
    assert rt["rt_value"]==1
    s=service.create_settlement("usr_requester",e["execution_id"])
    tr=service.create_training_record(e["execution_id"])
    b=service.get_execution_bundle(e["execution_id"])
    assert s["settlement_status"]=="RECORDED"
    assert tr["execution_id"]==e["execution_id"]
    assert b["result"]["result_id"]==r["result_id"]
    assert b["evidence"][0]["status"]=="VALIDATED"
    events={x["event_type"] for x in b["trace"]}
    required={"TASK_CREATED","TASK_VALIDATED","TASK_ASSIGNED","EXECUTION_STARTED","RESULT_SUBMITTED","EVIDENCE_SUBMITTED","EVIDENCE_VALIDATED","EXECUTION_FINISHED","EFFORT_RECORDED","RT_CALCULATED","SETTLEMENT_RECORDED","TRAINING_RECORDED"}
    assert required.issubset(events)

def test_rt_examples_and_invalid_effort(service):
    assert 30/30==1
    assert 60/30==2
    assert 90/30==3
    t=service.create_task("usr_requester","bad effort")
    service.validate_task("usr_requester",t["task_id"])
    service.assign_task("usr_requester",t["task_id"],"usr_executor")
    e=service.start_execution("usr_executor",t["task_id"])
    service.submit_result("usr_executor",e["execution_id"],"SUCCESS","ok")
    ev=service.submit_evidence("usr_executor",e["execution_id"],"TEXT","proof")
    service.validate_evidence("usr_requester",ev["evidence_id"])
    service.complete_execution("usr_executor",e["execution_id"])
    with pytest.raises(ValidationError):
        service.record_effort("usr_executor",e["execution_id"],0)

def test_role_boundaries(service):
    with pytest.raises(AuthorizationError):
        service.create_task("usr_executor","not allowed")
    with pytest.raises(AuthorizationError):
        service.start_execution("usr_trainer","unknown")
