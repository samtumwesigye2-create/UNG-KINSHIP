from sqlalchemy import select
from models import Person
from services import ancestors,descendants

def common_ancestors(db,family_id,left_id,right_id):
    return sorted(set(ancestors(db,family_id,left_id)) & set(ancestors(db,family_id,right_id)))
def find_duplicate_candidates(db,family_id,name):
    normalized=' '.join(name.lower().split())
    return [p for p in db.scalars(select(Person).where(Person.family_id==family_id)).all() if ' '.join(p.name.lower().split())==normalized]
