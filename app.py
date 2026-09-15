from fastapi import FastAPI,Depends,HTTPException,Header
from fastapi.responses import HTMLResponse,PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import Base,engine,get_db
from models import Family,Person,DNARecord,AuditEvent,Record
from services import create_family,register_person,add_relationship,encode,ancestors,descendants,audit

Base.metadata.create_all(bind=engine)
app=FastAPI(title='UNG-KINSHIP',version='1.0.0')
class FamilyIn(BaseModel): name:str
class PersonIn(BaseModel): name:str; living:bool=True; biography:str|None=None
class RelIn(BaseModel): source_id:int; target_id:int; relationship_type:str; status:str='accepted'; provenance:str|None=None
class DNAIn(BaseModel): provider:str; summary:str; consent:bool
class GedcomIn(BaseModel): text:str
class RecordIn(BaseModel): person_id:int|None=None; event_type:str; title:str; event_date:str|None=None; source:str|None=None

def person_out(p): return {'id':p.id,'family_id':p.family_id,'member_id':p.member_id,'lineage_code':p.lineage_code,'name':p.name,'living':p.living,'biography':p.biography}
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/v1/families',status_code=201)
def families(x:FamilyIn,db:Session=Depends(get_db)):
    f=create_family(db,x.name); return {'id':f.id,'family_code':f.family_code,'name':f.name,'public':f.public}
@app.post('/v1/families/{fid}/people',status_code=201)
def people(fid:int,x:PersonIn,db:Session=Depends(get_db)):
    try: p=register_person(db,fid,x.name,x.living); p.biography=x.biography; db.commit(); return person_out(p)
    except ValueError as e: raise HTTPException(404,str(e))
@app.patch('/v1/families/{fid}/people/{pid}')
def update_person(fid:int,pid:int,x:PersonIn,db:Session=Depends(get_db)):
    p=db.get(Person,pid)
    if not p or p.family_id!=fid: raise HTTPException(404,'person not found')
    stable=p.member_id; p.name=x.name; p.living=x.living; p.biography=x.biography; audit(db,fid,'person.updated',stable); db.commit(); return person_out(p)
@app.post('/v1/families/{fid}/relationships',status_code=201)
def relationships(fid:int,x:RelIn,db:Session=Depends(get_db)):
    try: r=add_relationship(db,fid,x.source_id,x.target_id,x.relationship_type,x.status,x.provenance); return {'id':r.id,'type':r.relationship_type,'status':r.status}
    except PermissionError as e: raise HTTPException(403,str(e))
    except RuntimeError as e: raise HTTPException(409,str(e))
    except ValueError as e: raise HTTPException(422,str(e))
@app.post('/v1/families/{fid}/encode')
def encoder(fid:int,db:Session=Depends(get_db)): return [person_out(p) for p in encode(db,fid)]
@app.get('/v1/families/{fid}/tree/{pid}')
def tree(fid:int,pid:int,db:Session=Depends(get_db)): return {'person_id':pid,'ancestors':ancestors(db,fid,pid),'descendants':descendants(db,fid,pid)}
@app.get('/v1/families/{fid}/search')
def search(fid:int,q:str='',db:Session=Depends(get_db)): return [person_out(p) for p in db.scalars(select(Person).where(Person.family_id==fid,Person.name.ilike(f'%{q}%'))).all()]
@app.post('/v1/families/{fid}/records',status_code=201)
def add_record(fid:int,x:RecordIn,db:Session=Depends(get_db)):
    r=Record(family_id=fid,**x.model_dump()); db.add(r); audit(db,fid,'record.created',x.title); db.commit(); return {'id':r.id,'title':r.title}
@app.get('/v1/families/{fid}/timeline')
def timeline(fid:int,db:Session=Depends(get_db)): return [{'id':r.id,'title':r.title,'event_type':r.event_type,'event_date':r.event_date} for r in db.scalars(select(Record).where(Record.family_id==fid).order_by(Record.event_date,Record.id)).all()]
@app.post('/v1/families/{fid}/people/{pid}/dna',status_code=201)
def dna_add(fid:int,pid:int,x:DNAIn,db:Session=Depends(get_db)):
    p=db.get(Person,pid)
    if not p or p.family_id!=fid: raise HTTPException(404,'person not found')
    d=DNARecord(family_id=fid,person_id=pid,**x.model_dump()); db.add(d); audit(db,fid,'dna.created','protected'); db.commit(); return {'id':d.id,'consent':d.consent}
@app.get('/v1/families/{fid}/people/{pid}/dna')
def dna_get(fid:int,pid:int,x_protected_access:str|None=Header(None),db:Session=Depends(get_db)):
    if x_protected_access!='true': raise HTTPException(403,'protected access required')
    return [{'id':d.id,'provider':d.provider,'summary':d.summary,'consent':d.consent,'revoked':d.revoked} for d in db.scalars(select(DNARecord).where(DNARecord.family_id==fid,DNARecord.person_id==pid,DNARecord.revoked==False)).all()]
@app.delete('/v1/families/{fid}/people/{pid}/dna/{did}')
def dna_revoke(fid:int,pid:int,did:int,db:Session=Depends(get_db)):
    d=db.get(DNARecord,did)
    if not d or d.family_id!=fid or d.person_id!=pid: raise HTTPException(404,'DNA record not found')
    d.revoked=True; audit(db,fid,'dna.revoked','protected'); db.commit(); return {'revoked':True}
@app.post('/v1/families/{fid}/gedcom/stage')
def ged_stage(fid:int,x:GedcomIn):
    if '0 HEAD' not in x.text or '0 TRLR' not in x.text: raise HTTPException(422,'invalid GEDCOM')
    return {'valid':True,'people':x.text.count(' INDI'),'relationships':x.text.count(' FAM')}
@app.get('/v1/families/{fid}/gedcom/export',response_class=PlainTextResponse)
def ged_export(fid:int,db:Session=Depends(get_db)):
    out=['0 HEAD','1 SOUR UNG-KINSHIP']
    for p in db.scalars(select(Person).where(Person.family_id==fid)).all(): out += [f'0 @I{p.id}@ INDI',f'1 NAME {p.name}']
    out.append('0 TRLR'); return '\n'.join(out)
@app.get('/v1/families/{fid}/audit')
def audits(fid:int,db:Session=Depends(get_db)): return [{'id':a.id,'action':a.action,'detail':a.detail,'created_at':a.created_at.isoformat()} for a in db.scalars(select(AuditEvent).where(AuditEvent.family_id==fid).order_by(AuditEvent.id)).all()]
@app.get('/',response_class=HTMLResponse)
def ui():
    return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-KINSHIP</title><style>body{font-family:system-ui;margin:0;background:#f6f7f9}header{padding:24px;background:#111;color:white}nav{display:flex;gap:12px;flex-wrap:wrap;padding:14px}button{padding:12px;border:0;border-radius:10px;background:white;box-shadow:0 1px 5px #ccc}main{padding:24px}.card{background:white;padding:20px;border-radius:16px;max-width:900px}</style></head><body><header><h1>UNG-KINSHIP</h1><p>Family Registry & Lineage Encoder</p></header><nav>''' + ''.join(f'<button>{x}</button>' for x in ['Family Tree','People','Families','Encoder','Ancestry/DNA','Records','Timeline','Search','Administration']) + '''</nav><main><div class="card"><h2>Family Tree</h2><p>Select a family and person to explore ancestors, descendants, records and lineage codes.</p></div></main></body></html>'''
