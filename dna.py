from sqlalchemy import select
from models import DNARecord

def create_dna_record(db,family_id,person_id,provider,summary,consent):
    d=DNARecord(family_id=family_id,person_id=person_id,provider=provider,summary=summary,consent=consent); db.add(d); db.commit(); return d
def get_dna_records(db,family_id,person_id,protected_access=False):
    if not protected_access: raise PermissionError('protected access required')
    return db.scalars(select(DNARecord).where(DNARecord.family_id==family_id,DNARecord.person_id==person_id,DNARecord.revoked==False)).all()
def revoke_dna(db,record): record.revoked=True; db.commit(); return record
