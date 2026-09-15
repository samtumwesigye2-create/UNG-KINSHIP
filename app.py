from fastapi import FastAPI,Depends,HTTPException,Header
from fastapi.responses import HTMLResponse,PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import Base,engine,get_db
from models import Family,Person,DNARecord,AuditEvent,Record
from services import create_family,register_person,add_relationship,encode,ancestors,descendants,audit

Base.metadata.create_all(bind=engine)
app=FastAPI(title='UNG-KINSHIP',version='1.1.0')
class FamilyIn(BaseModel): name:str
class PersonIn(BaseModel): name:str; living:bool=True; biography:str|None=None
class RelIn(BaseModel): source_id:int; target_id:int; relationship_type:str; status:str='accepted'; provenance:str|None=None
class DNAIn(BaseModel): provider:str; summary:str; consent:bool
class GedcomIn(BaseModel): text:str
class RecordIn(BaseModel): person_id:int|None=None; event_type:str; title:str; event_date:str|None=None; source:str|None=None

def person_out(p): return {'id':p.id,'family_id':p.family_id,'member_id':p.member_id,'lineage_code':p.lineage_code,'name':p.name,'living':p.living,'biography':p.biography}
def family_out(f): return {'id':f.id,'family_code':f.family_code,'name':f.name,'public':f.public}
@app.get('/health')
def health(): return {'status':'ok'}
@app.get('/v1/families')
def list_families(db:Session=Depends(get_db)): return [family_out(f) for f in db.scalars(select(Family).order_by(Family.id)).all()]
@app.post('/v1/families',status_code=201)
def families(x:FamilyIn,db:Session=Depends(get_db)):
    f=create_family(db,x.name); return family_out(f)
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
def search(fid:int,q:str='',db:Session=Depends(get_db)): return [person_out(p) for p in db.scalars(select(Person).where(Person.family_id==fid,Person.name.ilike(f'%{q}%')).order_by(Person.id)).all()]
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

UI='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>UNG-KINSHIP</title><style>
*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f3f5f7;color:#111}header{padding:34px 24px;background:linear-gradient(135deg,#0b0c0d,#24272b);color:white}header h1{font-size:34px;margin:0 0 8px;letter-spacing:.5px}header p{margin:0;color:#d8dce1}.toolbar{position:sticky;top:0;z-index:5;background:#f3f5f7eF;backdrop-filter:blur(14px);padding:12px;display:flex;gap:8px;overflow:auto;border-bottom:1px solid #e2e5e9}.tab{white-space:nowrap;background:white;border:1px solid #e2e5e9;border-radius:12px;padding:10px 14px;font-weight:650;color:#1769e0}.tab.active{background:#111;color:white}.shell{max-width:1100px;margin:auto;padding:16px}.selectors{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}select,input,textarea{width:100%;padding:12px;border:1px solid #d8dce2;border-radius:11px;background:white;font-size:16px}button.action{padding:12px 15px;border:0;border-radius:11px;background:#111;color:white;font-weight:700;font-size:15px}.secondary{background:#1769e0!important}.grid{display:grid;grid-template-columns:1.3fr .7fr;gap:14px}.card{background:white;border:1px solid #e5e7eb;border-radius:18px;padding:18px;box-shadow:0 4px 18px #0000000b}.card h2,.card h3{margin-top:0}.panel{display:none}.panel.active{display:block}.form{display:grid;gap:10px}.tree{min-height:300px;background:linear-gradient(#fafbfc,#f5f7f9);border:1px dashed #cfd5dc;border-radius:16px;padding:16px;overflow:auto}.tree-level{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:12px 0}.person{min-width:145px;background:white;border:1px solid #dfe3e8;border-radius:13px;padding:12px;text-align:center;box-shadow:0 2px 8px #0000000c}.person strong{display:block}.code{font:12px ui-monospace,monospace;color:#647080;margin-top:5px}.muted{color:#69727d}.list{display:grid;gap:8px}.row{padding:11px;border:1px solid #e4e7eb;border-radius:11px;background:#fafbfc}.status{margin-top:10px;min-height:20px;color:#1769e0;font-weight:650}@media(max-width:720px){header{padding:30px 22px}.grid{grid-template-columns:1fr}.selectors{grid-template-columns:1fr}.shell{padding:12px}.tree{min-height:250px}.card{padding:15px}}
</style></head><body><header><h1>UNG-KINSHIP</h1><p>Family Registry & Lineage Encoder</p></header><nav class="toolbar">''' + ''.join(f'<button class="tab" data-panel="{x.lower().replace("/","-").replace(" ","-")}">{x}</button>' for x in ['Family Tree','People','Families','Encoder','Ancestry/DNA','Records','Timeline','Search','Administration']) + '''</nav><div class="shell"><div class="selectors"><select id="familySelect"><option value="">Select family</option></select><select id="personSelect"><option value="">Select person</option></select></div>
<section id="family-tree" class="panel active"><div class="grid"><div class="card"><h2>Family Tree</h2><p class="muted">Explore ancestors and descendants from the selected person.</p><div id="treeCanvas" class="tree"><p class="muted">Create or select a family and person to begin.</p></div></div><div class="card"><h3>Relationship</h3><div class="form"><select id="relationshipSource"></select><select id="relationshipType"><option value="biological_parent">Biological parent of</option><option value="adoptive_parent">Adoptive parent of</option><option value="guardian">Guardian of</option><option value="spouse">Spouse / partner</option><option value="sibling">Sibling</option><option value="half_sibling">Half sibling</option><option value="twin">Twin</option><option value="step_family">Step family</option><option value="disputed_parent">Disputed parent</option></select><select id="relationshipTarget"></select><button class="action" onclick="addRelationship()">Add Relationship</button></div><div id="treeStatus" class="status"></div></div></div></section>
<section id="people" class="panel"><div class="grid"><div class="card"><h2>People</h2><div id="peopleList" class="list"></div></div><div class="card"><h3>Add Person</h3><div class="form"><input id="personName" placeholder="Full name"><label><input id="personLiving" type="checkbox" checked style="width:auto"> Living</label><textarea id="personBio" placeholder="Biography / notes"></textarea><button class="action secondary" onclick="addPerson()">Register Person</button></div><div id="personStatus" class="status"></div></div></div></section>
<section id="families" class="panel"><div class="grid"><div class="card"><h2>Families</h2><div id="familyList" class="list"></div></div><div class="card"><h3>Create Family</h3><div class="form"><input id="familyName" placeholder="Family name"><button class="action secondary" onclick="createFamily()">Create Family Registry</button></div><div id="familyStatus" class="status"></div></div></div></section>
<section id="encoder" class="panel"><div class="card"><h2>Lineage Encoder</h2><p class="muted">Permanent member IDs remain stable. Lineage codes are regenerated from current genealogy.</p><button id="encodeButton" class="action" onclick="runEncoder()">Generate / Refresh Lineage Codes</button><div id="encoderStatus" class="status"></div><div id="encoderList" class="list" style="margin-top:14px"></div></div></section>
<section id="ancestry-dna" class="panel"><div class="card"><h2>Ancestry/DNA</h2><p>Protected ancestry workspace. DNA records remain separately permissioned.</p></div></section><section id="records" class="panel"><div class="card"><h2>Records</h2><p>Family evidence and life-event records.</p></div></section><section id="timeline" class="panel"><div class="card"><h2>Timeline</h2><p>Chronological family events.</p></div></section><section id="search" class="panel"><div class="card"><h2>Search</h2><p>Search the selected family registry.</p></div></section><section id="administration" class="panel"><div class="card"><h2>Administration</h2><p>Family permissions, audit history and interoperability controls.</p></div></section></div>
<script>
let families=[],people=[]; const $=id=>document.getElementById(id); async function json(url,opt){let r=await fetch(url,opt);let d=await r.json().catch(()=>({detail:r.statusText}));if(!r.ok)throw Error(d.detail||'Request failed');return d}
function familyId(){return Number($('familySelect').value)} function personId(){return Number($('personSelect').value)}
async function refreshFamilies(selectId){families=await fetch('/v1/families').then(r=>r.json()); $('familySelect').innerHTML='<option value="">Select family</option>'+families.map(f=>`<option value="${f.id}">${f.name} · ${f.family_code}</option>`).join(''); if(selectId)$('familySelect').value=selectId; renderFamilies(); await refreshPeople()}
async function refreshPeople(selectId){let fid=familyId();people=fid?await fetch(`/v1/families/${fid}/search?q=`).then(r=>r.json()):[];let opts='<option value="">Select person</option>'+people.map(p=>`<option value="${p.id}">${p.name}</option>`).join('');$('personSelect').innerHTML=opts;$('relationshipSource').innerHTML=opts;$('relationshipTarget').innerHTML=opts;if(selectId)$('personSelect').value=selectId;renderPeople();if(personId())loadTree();else $('treeCanvas').innerHTML='<p class="muted">Select a person to display the tree.</p>'}
function renderFamilies(){$('familyList').innerHTML=families.length?families.map(f=>`<div class="row"><strong>${f.name}</strong><div class="code">${f.family_code}</div></div>`).join(''):'<p class="muted">No families yet.</p>'}
function renderPeople(){$('peopleList').innerHTML=people.length?people.map(p=>`<div class="row"><strong>${p.name}</strong><div class="code">${p.member_id}${p.lineage_code?' · '+p.lineage_code:''}</div></div>`).join(''):'<p class="muted">No people registered.</p>'}
async function createFamily(){try{let f=await json('/v1/families',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('familyName').value})});$('familyName').value='';$('familyStatus').textContent=`Created ${f.name} (${f.family_code})`;await refreshFamilies(f.id)}catch(e){$('familyStatus').textContent=e.message}}
async function addPerson(){let fid=familyId();if(!fid)return $('personStatus').textContent='Select a family first.';try{let p=await json(`/v1/families/${fid}/people`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('personName').value,living:$('personLiving').checked,biography:$('personBio').value||null})});$('personName').value='';$('personBio').value='';$('personStatus').textContent=`Registered ${p.name} · ${p.member_id}`;await refreshPeople(p.id)}catch(e){$('personStatus').textContent=e.message}}
async function addRelationship(){let fid=familyId(),s=Number($('relationshipSource').value),t=Number($('relationshipTarget').value);if(!fid||!s||!t)return $('treeStatus').textContent='Select family and both people.';try{await json(`/v1/families/${fid}/relationships`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source_id:s,target_id:t,relationship_type:$('relationshipType').value})});$('treeStatus').textContent='Relationship saved.';$('personSelect').value=t;await loadTree()}catch(e){$('treeStatus').textContent=e.message}}
async function loadTree(){let fid=familyId(),pid=personId();if(!fid||!pid)return;let t=await fetch(`/v1/families/${fid}/tree/${pid}`).then(r=>r.json()),by=Object.fromEntries(people.map(p=>[p.id,p])),node=id=>{let p=by[id];return p?`<div class="person"><strong>${p.name}</strong><div class="code">${p.lineage_code||p.member_id}</div></div>`:''};$('treeCanvas').innerHTML=`<div class="tree-level">${t.ancestors.map(node).join('')||'<span class="muted">No known ancestors</span>'}</div><div class="tree-level">${node(pid)}</div><div class="tree-level">${t.descendants.map(node).join('')||'<span class="muted">No known descendants</span>'}</div>`}
async function runEncoder(){let fid=familyId();if(!fid)return $('encoderStatus').textContent='Select a family first.';try{let rows=await json(`/v1/families/${fid}/encode`,{method:'POST'});$('encoderStatus').textContent=`Encoded ${rows.length} people.`;$('encoderList').innerHTML=rows.map(p=>`<div class="row"><strong>${p.name}</strong><div class="code">Member: ${p.member_id}<br>Lineage: ${p.lineage_code}</div></div>`).join('');await refreshPeople(personId())}catch(e){$('encoderStatus').textContent=e.message}}
document.querySelectorAll('.tab').forEach((b,i)=>{if(i===0)b.classList.add('active');b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');$(b.dataset.panel).classList.add('active')}});$('familySelect').onchange=()=>refreshPeople();$('personSelect').onchange=()=>loadTree();refreshFamilies();
</script></body></html>'''
@app.get('/',response_class=HTMLResponse)
def ui(): return UI
