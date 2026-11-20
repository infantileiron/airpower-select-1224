from fastapi import HTTPException
from src.models.entities import Run,Pilot

def ensure_run(s,i):
 row=s.get(Run,i)
 if not row:raise HTTPException(404,'模型版本不存在')
 return row
def ensure_pilot(s,i):
 row=s.get(Pilot,i)
 if not row:raise HTTPException(404,'调压试点不存在')
 return row
