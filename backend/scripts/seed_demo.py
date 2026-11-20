import random,math,logging
from datetime import datetime,timedelta
from src.config.database import Base,engine,Session
from src.models.entities import User,Sample,Pilot
from src.utils.security import hash_password
def seed():
 Base.metadata.create_all(engine);rng=random.Random(3110)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  for i in range(240):
   hour=(datetime(2026,11,1)+timedelta(hours=i)).strftime('%Y-%m-%dT%H:00');trial=i>=192;flow=round(8+3*math.sin(i*math.pi/12)+rng.uniform(-1,1),3);pressure=round(rng.uniform(6.0,6.6) if trial else rng.uniform(5.8,7.5),3);temp=round(22+5*math.sin(i*math.pi/12)+rng.uniform(-2,2),3);machines=2+i%4;noise=round(rng.uniform(-3,3),3);kwh=round(40+14*flow+5*machines+2*pressure+.15*temp+rng.gauss(0,2.5)-(4 if trial else 0),3)
   if not s.query(Sample).filter_by(hour=hour).first():s.add(Sample(hour=hour,flow=flow,pressure=pressure,temperature=temp,machines=machines,sensor_noise=noise,kwh=kwh,note='ZX-A01空压站；本地整点小时；sensor_noise为无关对照特征'))
  if not s.query(Pilot).filter_by(name='ZX-A01调压试点1109').first():
   p=Pilot(name='ZX-A01调压试点1109',start_hour='2026-11-09T00:00',end_hour='2026-11-10T23:00',target_pressure=6.3,note='演示：末两日降压运行，对照取自11月1日至8日同班次小时')
   s.add(p);s.flush()
   try:
    from src.services.pilot import evaluate
    evaluate(s,p)
   except Exception:logging.exception('seed pilot evaluate')
  s.commit();print({'users':s.query(User).count(),'samples':s.query(Sample).count(),'pilots':s.query(Pilot).count()})
if __name__=='__main__':seed()
