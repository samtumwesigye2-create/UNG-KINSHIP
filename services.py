from sqlalchemy import select
from models import Family,Person,Relationship,LineageHistory,AuditEvent
PARENT_TYPES={'biological_parent','adoptive_parent','guardian'}
REL_TYPES=PARENT_TYPES|{'spouse','partner','former_spouse','former_partner','step_family','sibling','half_sibling','twin','unknown_parent','disputed_parent'}

def audit(db,fid,action,detail=''):
    db.add(AuditEvent(family_id=fid,action=action,detail=detail)); db.flush()
def create_family(db,name):
    n=(db.scalar(select(Family.id).order_by(Family.id.desc())) or 0)+1; f=Family(name=name,family_code=f'FAM-{n:05d}'); db.add(f); db.flush(); audit(db,f.id,'family.created',name); db.commit(); return f
def register_person(db,fid,name,living=True):
    f=db.get(Family,fid)
    if not f: raise ValueError('family not found')
    count=len(db.scalars(select(Person).where(Person.family_id==fid)).all())+1; p=Person(family_id=fid,member_id=f'{f.family_code}-{count:03d}',name=name,living=living); db.add(p); db.flush(); audit(db,fid,'person.created',p.member_id); db.commit(); return p
def _parents(db,fid,pid): return [r.source_id for r in db.scalars(select(Relationship).where(Relationship.family_id==fid,Relationship.target_id==pid,Relationship.relationship_type.in_(PARENT_TYPES))).all()]
def ancestors(db,fid,pid):
    seen=set(); stack=_parents(db,fid,pid)
    while stack:
        x=stack.pop()
        if x in seen: continue
        seen.add(x); stack.extend(_parents(db,fid,x))
    return sorted(seen)
def descendants(db,fid,pid):
    seen=set(); stack=[pid]
    while stack:
        x=stack.pop()
        for r in db.scalars(select(Relationship).where(Relationship.family_id==fid,Relationship.source_id==x,Relationship.relationship_type.in_(PARENT_TYPES))).all():
            if r.target_id not in seen: seen.add(r.target_id); stack.append(r.target_id)
    return sorted(seen)
def add_relationship(db,fid,source,target,kind,status='accepted',provenance=None):
    if kind not in REL_TYPES: raise ValueError('unsupported relationship')
    a,b=db.get(Person,source),db.get(Person,target)
    if not a or not b or a.family_id!=fid or b.family_id!=fid: raise PermissionError('cross-family relationship')
    if source==target or (kind in PARENT_TYPES and source in descendants(db,fid,target)): raise RuntimeError('relationship cycle')
    r=Relationship(family_id=fid,source_id=source,target_id=target,relationship_type=kind,status=status,provenance=provenance); db.add(r); audit(db,fid,'relationship.created',kind); db.commit(); return r
def encode(db,fid):
    people=db.scalars(select(Person).where(Person.family_id==fid).order_by(Person.id)).all(); ids={p.id for p in people}; parent_map={p.id:_parents(db,fid,p.id) for p in people}; generation={}; roots=[p.id for p in people if not parent_map[p.id]]
    for rid in roots: generation[rid]=1
    changed=True
    while changed:
        changed=False
        for p in people:
            known=[generation[x] for x in parent_map[p.id] if x in generation]
            if known and generation.get(p.id)!=max(known)+1: generation[p.id]=max(known)+1; changed=True
    branch={rid:i+1 for i,rid in enumerate(roots)}
    for p in people:
        if p.id not in branch:
            ps=parent_map[p.id]; branch[p.id]=branch.get(ps[0],1) if ps else 1
        code=f'{db.get(Family,fid).family_code[-5:]}-G{generation.get(p.id,1):02d}-B{branch[p.id]:02d}-{p.member_id[-3:]}'
        if p.lineage_code!=code: p.lineage_code=code; db.add(LineageHistory(person_id=p.id,lineage_code=code))
    audit(db,fid,'lineage.encoded'); db.commit(); return people
