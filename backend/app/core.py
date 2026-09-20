from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RT_NS = 30

class DomainError(Exception):
    status_code = 400

class NotFoundError(DomainError):
    status_code = 404

class AuthorizationError(DomainError):
    status_code = 403

class ValidationError(DomainError):
    status_code = 422

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def write_local_artifact(storage_root: Path, execution_id: str, evidence_id: str, evidence_text: str) -> str:
    target_dir = storage_root / "evidence" / execution_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{evidence_id}.txt"
    target.write_text(evidence_text, encoding="utf-8")
    return str(target.relative_to(storage_root)).replace("\\", "/")
