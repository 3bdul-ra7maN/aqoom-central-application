# AQOOM Central Application MVP API

POST /tasks
POST /tasks/{task_id}/validate
POST /tasks/{task_id}/assign
POST /executions/start
POST /executions/{execution_id}/result
POST /executions/{execution_id}/evidence
POST /evidence/{evidence_id}/validate
POST /executions/{execution_id}/complete
POST /executions/{execution_id}/effort
POST /executions/{execution_id}/rt
POST /executions/{execution_id}/settlement
POST /executions/{execution_id}/training
GET /executions/{execution_id}/trace
GET /training

RT rule: 1 RT = 30 ns.
Settlement means Settlement Record in MVP, not payment.
