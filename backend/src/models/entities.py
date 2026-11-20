from sqlalchemy import Column,Integer,String,Float,JSON,Text,ForeignKey
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True);password=Column(String(200));role=Column(String(20))
class Sample(Base):
 __tablename__='samples'
 id=Column(Integer,primary_key=True);hour=Column(String(30),unique=True,nullable=False);pressure=Column(Float);flow=Column(Float);temperature=Column(Float);machines=Column(Integer);sensor_noise=Column(Float);kwh=Column(Float);note=Column(Text,default='')
class Run(Base):
 __tablename__='runs'
 id=Column(Integer,primary_key=True);name=Column(String(100));features=Column(JSON);alphas=Column(JSON);state=Column(String(20),default='queued');result=Column(JSON);error=Column(Text,default='')
class Review(Base):
 __tablename__='reviews'
 id=Column(Integer,primary_key=True);run_id=Column(Integer,ForeignKey('runs.id'));title=Column(String(100));finding=Column(Text);action=Column(Text);status=Column(String(20),default='draft')
class Pilot(Base):
 __tablename__='pilots'
 id=Column(Integer,primary_key=True);name=Column(String(100),nullable=False);start_hour=Column(String(30),nullable=False);end_hour=Column(String(30),nullable=False);target_pressure=Column(Float);note=Column(Text,default='');status=Column(String(20),default='registered');eval_version=Column(Integer,default=0);result=Column(JSON);error=Column(Text,default='');approved_by=Column(String(100),default='');approved_at=Column(String(40),default='')
class Pairing(Base):
 __tablename__='pairings'
 id=Column(Integer,primary_key=True);pilot_id=Column(Integer,ForeignKey('pilots.id'),nullable=False);pilot_hour=Column(String(30),nullable=False);control_hour=Column(String(30),unique=True,nullable=False);shift=Column(Integer);machines=Column(Integer);pilot_flow=Column(Float);control_flow=Column(Float);flow_diff=Column(Float);pilot_temp=Column(Float);control_temp=Column(Float);temp_diff=Column(Float);pilot_kwh=Column(Float);control_kwh=Column(Float);saving=Column(Float)
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
