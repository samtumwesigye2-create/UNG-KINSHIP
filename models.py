from datetime import datetime
from sqlalchemy import String,Integer,Boolean,ForeignKey,Text,DateTime,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from database import Base

class Family(Base):
    __tablename__='families'; id:Mapped[int]=mapped_column(primary_key=True); family_code:Mapped[str]=mapped_column(String(16),unique=True); name:Mapped[str]=mapped_column(String(200)); public:Mapped[bool]=mapped_column(Boolean,default=False)
class Person(Base):
    __tablename__='people'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id'),index=True); member_id:Mapped[str]=mapped_column(String(32),unique=True); name:Mapped[str]=mapped_column(String(240)); living:Mapped[bool]=mapped_column(Boolean,default=True); biography:Mapped[str|None]=mapped_column(Text,nullable=True); lineage_code:Mapped[str|None]=mapped_column(String(40),nullable=True)
class Relationship(Base):
    __tablename__='relationships'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id'),index=True); source_id:Mapped[int]=mapped_column(ForeignKey('people.id')); target_id:Mapped[int]=mapped_column(ForeignKey('people.id')); relationship_type:Mapped[str]=mapped_column(String(40)); status:Mapped[str]=mapped_column(String(30),default='accepted'); provenance:Mapped[str|None]=mapped_column(Text,nullable=True)
class LineageHistory(Base):
    __tablename__='lineage_history'; id:Mapped[int]=mapped_column(primary_key=True); person_id:Mapped[int]=mapped_column(ForeignKey('people.id')); lineage_code:Mapped[str]=mapped_column(String(40)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class FamilyRole(Base):
    __tablename__='family_roles'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id')); subject:Mapped[str]=mapped_column(String(120)); role:Mapped[str]=mapped_column(String(30)); protected_access:Mapped[bool]=mapped_column(Boolean,default=False); __table_args__=(UniqueConstraint('family_id','subject'),)
class Record(Base):
    __tablename__='records'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id')); person_id:Mapped[int|None]=mapped_column(ForeignKey('people.id'),nullable=True); event_type:Mapped[str]=mapped_column(String(50)); title:Mapped[str]=mapped_column(String(240)); event_date:Mapped[str|None]=mapped_column(String(32),nullable=True); source:Mapped[str|None]=mapped_column(Text,nullable=True)
class DNARecord(Base):
    __tablename__='dna_records'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id')); person_id:Mapped[int]=mapped_column(ForeignKey('people.id')); provider:Mapped[str]=mapped_column(String(120)); summary:Mapped[str]=mapped_column(Text); consent:Mapped[bool]=mapped_column(Boolean,default=False); revoked:Mapped[bool]=mapped_column(Boolean,default=False)
class AuditEvent(Base):
    __tablename__='audit_events'; id:Mapped[int]=mapped_column(primary_key=True); family_id:Mapped[int]=mapped_column(ForeignKey('families.id'),index=True); action:Mapped[str]=mapped_column(String(120)); detail:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
