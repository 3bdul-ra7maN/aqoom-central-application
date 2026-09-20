from pathlib import Path
from .app.db import Database
from .app.services import AQOOMService
from .app.web import serve

if __name__=="__main__":
    root=Path(__file__).resolve().parent
    svc=AQOOMService(Database(root/"storage"/"aqoom.db"),root/"storage")
    svc.seed_demo_users()
    serve(svc)
