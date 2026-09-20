from pathlib import Path
from backend.app.db import Database
from backend.app.services import AQOOMService
from backend.app.web import serve

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    svc=AQOOMService(Database(root/"backend"/"storage"/"aqoom.db"),root/"backend"/"storage")
    svc.seed_demo_users()
    serve(svc)
