from sqlalchemy import select
from models import Record

def create_record(db,family_id,person_id,event_type,title,event_date=None,source=None):
    r=Record(family_id=family_id,person_id=person_id,event_type=event_type,title=title,event_date=event_date,source=source); db.add(r); db.commit(); return r
def timeline(db,family_id): return db.scalars(select(Record).where(Record.family_id==family_id).order_by(Record.event_date,Record.id)).all()
