import os,json,logging
from datetime import datetime,timezone
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Sample,Run,Review,Audit,Pilot,Pairing
from src.schemas.business import Login,SampleInput,RunInput,ReviewInput,PilotInput,ApproveInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services.pilot import evaluate as evaluate_matching,recompute_unsigned,hours_between
from src.controllers.business import ensure_run,ensure_pilot
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/samples')
def samples(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Sample).order_by(Sample.hour).all()]
def refresh_unsigned(s,u):
 try:
  n=recompute_unsigned(s);s.commit()
  if n:audit(s,u,f'样本变动触发重算{n}个未签核试点配对')
 except Exception:s.rollback();logging.exception('recompute unsigned pilots')
@router.post('/samples')
def create(data:SampleInput,u=Depends(editor),s=Depends(db)):
 r=Sample(**data.model_dump());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'该小时已存在，请使用修订功能')
 audit(s,u,'录入小时 '+r.hour);refresh_unsigned(s,u);return dump(r)
@router.put('/samples/{i}')
def edit(i:int,data:SampleInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Sample,i)
 if not r:raise HTTPException(404,'小时样本不存在')
 for k,v in data.model_dump().items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'小时重复')
 audit(s,u,'修订样本 '+str(i));refresh_unsigned(s,u);return dump(r)
@router.get('/runs')
def runs(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Run).order_by(Run.id.desc()).all()]
@router.post('/runs')
def train(data:RunInput,u=Depends(editor),s=Depends(db)):
 rows=[dump(r) for r in s.query(Sample).order_by(Sample.hour).all()];r=Run(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('airpower:runs',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，请稍后重试';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交模型 '+str(r.id));return dump(r)
@router.get('/runs/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_run(s,i))
@router.get('/runs/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_run(s,i)
 if r.state!='done':raise HTTPException(409,'仅成功版本可导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="airpower-select-{i}.json"'})
@router.get('/reviews')
def reviews(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Review).order_by(Review.id.desc()).all()]
@router.post('/reviews')
def review(data:ReviewInput,u=Depends(editor),s=Depends(db)):
 if ensure_run(s,data.run_id).state!='done':raise HTTPException(409,'模型计算完成后才能起草评议')
 r=Review(**data.model_dump());s.add(r);s.commit();audit(s,u,'起草节能评议 '+str(r.id));return dump(r)
@router.put('/reviews/{i}')
def edit_review(i:int,data:ReviewInput,u=Depends(editor),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'评议不存在')
 if r.status!='draft':raise HTTPException(409,'已签核评议冻结，请新建')
 if ensure_run(s,data.run_id).state!='done':raise HTTPException(409,'需要已成功模型')
 for k,v in data.model_dump().items():setattr(r,k,v)
 s.commit();audit(s,u,'修订评议 '+str(i));return dump(r)
@router.post('/reviews/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'评议不存在')
 if r.status!='draft':raise HTTPException(409,'已签核评议不能重复签核')
 r.status='approved';s.commit();audit(s,u,'签核节能评议 '+str(i));return dump(r)
@router.get('/reviews/{i}/export')
def export_review(i:int,u=Depends(current),s=Depends(db)):
 r=s.get(Review,i)
 if not r:raise HTTPException(404,'评议不存在')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="airpower-review-{i}.json"'})
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
def pilot_detail(s,p):
 d=dump(p);d['pairs']=[dump(x) for x in s.query(Pairing).filter(Pairing.pilot_id==p.id).order_by(Pairing.pilot_hour).all()]
 return d
@router.get('/pilots')
def pilots(u=Depends(current),s=Depends(db)):
 out=[]
 for p in s.query(Pilot).order_by(Pilot.id.desc()).all():
  d=dump(p);d['pairs']=s.query(Pairing).filter(Pairing.pilot_id==p.id).count();out.append(d)
 return out
@router.post('/pilots')
def register_pilot(data:PilotInput,u=Depends(editor),s=Depends(db)):
 ph=hours_between(data.start_hour,data.end_hour)
 have={r[0] for r in s.query(Sample.hour).all()}
 missing=[h for h in ph if h not in have]
 if missing:raise HTTPException(409,f'试点时段缺少{len(missing)}个小时计量，请先补录（如 {missing[0]}）')
 rows=s.query(Pairing,Pilot).join(Pilot,Pairing.pilot_id==Pilot.id).filter(Pilot.status=='approved',Pairing.control_hour.in_(ph)).all()
 if rows:
  affected={}
  for pair,pl in rows:affected.setdefault('#'+str(pl.id)+' '+pl.name,[]).append(pair.control_hour)
  raise HTTPException(409,'试点时段覆盖已签核对照小时，受影响试点：'+'；'.join(f'{k}（{len(v)}小时，如{v[0]}）' for k,v in affected.items()))
 r=Pilot(**data.model_dump());s.add(r);s.commit();audit(s,u,'登记调压试点 '+str(r.id));return dump(r)
@router.get('/pilots/{i}')
def get_pilot(i:int,u=Depends(current),s=Depends(db)):return pilot_detail(s,ensure_pilot(s,i))
@router.post('/pilots/{i}/evaluate')
def evaluate_pilot(i:int,u=Depends(editor),s=Depends(db)):
 p=s.query(Pilot).filter(Pilot.id==i).with_for_update().first()
 if not p:raise HTTPException(404,'调压试点不存在')
 if p.status=='approved':raise HTTPException(409,'已签核试点的配对与原读数已锁定，不能重算')
 try:evaluate_matching(s,p);s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'对照小时被并发评估占用，请重试')
 audit(s,u,f'评估试点配对 {p.id} 第{p.eval_version}版');return pilot_detail(s,p)
@router.post('/pilots/{i}/approve')
def approve_pilot(i:int,data:ApproveInput,u=Depends(admin),s=Depends(db)):
 p=s.query(Pilot).filter(Pilot.id==i).with_for_update().first()
 if not p:raise HTTPException(404,'调压试点不存在')
 if p.status=='approved':raise HTTPException(409,'试点已签核，配对与原读数已锁定')
 if p.status!='evaluated':raise HTTPException(409,'请先完成配对评估再签核')
 if p.eval_version!=data.eval_version:raise HTTPException(409,'配对已在别处更新，请刷新核对后再签核')
 if not (p.result or {}).get('complete'):raise HTTPException(409,'负荷段缺少代表性配对，不能签核')
 p.status='approved';p.approved_by=u.email;p.approved_at=datetime.now(timezone.utc).isoformat()
 s.commit();audit(s,u,'签核调压试点 '+str(p.id));return pilot_detail(s,p)
@router.get('/pilots/{i}/export')
def export_pilot(i:int,u=Depends(current),s=Depends(db)):
 p=ensure_pilot(s,i)
 if p.status not in ('evaluated','approved'):raise HTTPException(409,'评估完成后才能导出')
 return Response(json.dumps(pilot_detail(s,p),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="airpower-pilot-{i}.json"'})
