from pathlib import Path
import shutil,tempfile
import pytest
from backend.app.db import Database
from backend.app.services import AQOOMService

@pytest.fixture
def service():
    root=Path(tempfile.mkdtemp(prefix="aqoom_mvp_"))
    svc=AQOOMService(Database(root/"db.sqlite"),root/"storage")
    svc.seed_demo_users()
    yield svc
    shutil.rmtree(root,ignore_errors=True)
