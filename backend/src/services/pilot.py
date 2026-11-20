import logging
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from src.constants.enums import MATCH_FLOW_TOL,MATCH_TEMP_TOL,SHIFT_HOURS
from src.models.entities import Sample,Pilot,Pairing
def hours_between(start,end):
 a=datetime.fromisoformat(start);b=datetime.fromisoformat(end);out=[]
 while a<=b:out.append(a.strftime('%Y-%m-%dT%H:00'));a+=timedelta(hours=1)
 return out
def shift_of(h):return datetime.fromisoformat(h).hour//SHIFT_HOURS
def match_hours(by_hour,pilot_hours,candidates,occupied):
 buckets=defaultdict(list)
 for c in candidates:buckets[(shift_of(c['hour']),c['machines'])].append(c)
 used=set();pairs=[];unmatched=[]
 for h in pilot_hours:
  ps=by_hour.get(h)
  if not ps:unmatched.append(dict(hour=h,reason='缺少该小时计量记录'));continue
  base=buckets.get((shift_of(h),ps['machines']),[])
  if not base:unmatched.append(dict(hour=h,reason='同班次同开机台数无更早对照记录'));continue
  fd=lambda c:abs(c['flow']-ps['flow']);td=lambda c:abs(c['temperature']-ps['temperature'])
  within=[c for c in base if fd(c)<=MATCH_FLOW_TOL and td(c)<=MATCH_TEMP_TOL]
  if not within:
   near=min(base,key=lambda c:fd(c)/MATCH_FLOW_TOL+td(c)/MATCH_TEMP_TOL)
   unmatched.append(dict(hour=h,reason=f'工况差距超限：最接近候选气量差{fd(near):.3f}m³/min（限{MATCH_FLOW_TOL}）、温度差{td(near):.3f}℃（限{MATCH_TEMP_TOL}）'));continue
  free=[c for c in within if c['hour'] not in occupied and c['hour'] not in used]
  if not free:unmatched.append(dict(hour=h,reason='可比对照小时已被其他试点占用'));continue
  best=min(free,key=lambda c:(fd(c)/MATCH_FLOW_TOL+td(c)/MATCH_TEMP_TOL,c['hour']))
  used.add(best['hour'])
  pairs.append(dict(pilot_hour=h,control_hour=best['hour'],shift=shift_of(h),machines=ps['machines'],pilot_flow=ps['flow'],control_flow=best['flow'],flow_diff=round(fd(best),3),pilot_temp=ps['temperature'],control_temp=best['temperature'],temp_diff=round(td(best),3),pilot_kwh=ps['kwh'],control_kwh=best['kwh'],saving=round(best['kwh']-ps['kwh'],3)))
 return pairs,unmatched
def evaluate(s,pilot):
 recs=[dict(hour=r.hour,flow=r.flow,temperature=r.temperature,machines=r.machines,kwh=r.kwh) for r in s.query(Sample).order_by(Sample.hour).all()]
 by_hour={r['hour']:r for r in recs}
 pilot_hours=hours_between(pilot.start_hour,pilot.end_hour)
 occupied={p.control_hour for p in s.query(Pairing).filter(Pairing.pilot_id!=pilot.id).all()}
 blocked=set()
 for pl in s.query(Pilot).all():blocked.update(hours_between(pl.start_hour,pl.end_hour))
 candidates=[r for r in recs if r['hour']<pilot.start_hour and r['hour'] not in blocked and r['hour'] not in occupied]
 pairs,unmatched=match_hours(by_hour,pilot_hours,candidates,occupied)
 s.query(Pairing).filter(Pairing.pilot_id==pilot.id).delete()
 for p in pairs:s.add(Pairing(pilot_id=pilot.id,**p))
 matched={p['pilot_hour'] for p in pairs};segments={}
 for h in pilot_hours:
  ps=by_hour.get(h);key=ps['machines'] if ps else None
  g=segments.setdefault(key,dict(machines=key,pilot_hours=0,matched=0));g['pilot_hours']+=1;g['matched']+=1 if h in matched else 0
 segs=sorted(segments.values(),key=lambda g:(g['machines'] is None,g['machines']))
 for g in segs:g['represented']=g['matched']>0
 total=round(sum(p['saving'] for p in pairs),3);ckwh=round(sum(p['control_kwh'] for p in pairs),3)
 pilot.result=dict(evaluated_at=datetime.now(timezone.utc).isoformat(),pilot_hours=len(pilot_hours),matched=len(pairs),segments=segs,unmatched=unmatched,total_saving_kwh=total,avg_saving_kwh=round(total/len(pairs),3) if pairs else None,control_kwh_sum=ckwh,pilot_kwh_sum=round(ckwh-total,3),saving_pct=round(100*total/ckwh,2) if ckwh else None,complete=bool(pairs) and all(g['represented'] for g in segs),tolerances=dict(flow=MATCH_FLOW_TOL,temperature=MATCH_TEMP_TOL,machines='相同',shift='同8小时班次'),method='对照小时取自试点开始之前、同8小时班次、同开机台数且不在任何试点时段内的小时；气量差与温度差在限值内按归一化距离择优；每个对照小时全站只用一次；节电差额=对照kWh−试点kWh。签核后配对与原读数锁定；样本修订只重算未签核试点。')
 pilot.eval_version=(pilot.eval_version or 0)+1;pilot.status='evaluated';pilot.error=''
 return pilot
def recompute_unsigned(s):
 pilots=s.query(Pilot).filter(Pilot.status=='evaluated').order_by(Pilot.id).all()
 if not pilots:return 0
 s.query(Pairing).filter(Pairing.pilot_id.in_([p.id for p in pilots])).delete(synchronize_session=False)
 done=0
 for p in pilots:
  try:
   with s.begin_nested():evaluate(s,p)
   done+=1
  except Exception as e:
   logging.exception('recompute pilot %s',p.id)
   try:
    with s.begin_nested():p.status='failed';p.error='自动重算失败，请手动重新评估：'+str(e)[:300]
   except Exception:logging.exception('mark pilot failed')
 s.flush()
 return done
