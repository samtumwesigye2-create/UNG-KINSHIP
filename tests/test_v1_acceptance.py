import pytest
from fastapi.testclient import TestClient
from app import app
from database import Base, engine

client = TestClient(app)

def setup_function():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)

def test_v1_family_identity_tree_encoder_privacy_and_interop():
    assert client.get('/health').json() == {'status':'ok'}
    a=client.post('/v1/families',json={'name':'Alpha'}).json(); b=client.post('/v1/families',json={'name':'Beta'}).json()
    assert a['family_code'] != b['family_code']
    root=client.post(f"/v1/families/{a['id']}/people",json={'name':'Ancestor','living':False}).json()
    child=client.post(f"/v1/families/{a['id']}/people",json={'name':'Child','living':True}).json()
    assert root['member_id'].startswith(a['family_code']+'-')
    r=client.post(f"/v1/families/{a['id']}/relationships",json={'source_id':root['id'],'target_id':child['id'],'relationship_type':'biological_parent'}); assert r.status_code==201
    cycle=client.post(f"/v1/families/{a['id']}/relationships",json={'source_id':child['id'],'target_id':root['id'],'relationship_type':'biological_parent'}); assert cycle.status_code==409
    codes=client.post(f"/v1/families/{a['id']}/encode").json(); assert all('-G' in x['lineage_code'] for x in codes)
    tree=client.get(f"/v1/families/{a['id']}/tree/{child['id']}").json(); assert root['id'] in tree['ancestors']
    dna=client.post(f"/v1/families/{a['id']}/people/{child['id']}/dna",json={'provider':'Example','summary':'private','consent':True}); assert dna.status_code==201
    assert client.get(f"/v1/families/{a['id']}/people/{child['id']}/dna").status_code==403
    assert client.get(f"/v1/families/{a['id']}/people/{child['id']}/dna",headers={'X-Protected-Access':'true'}).status_code==200
    staged=client.post(f"/v1/families/{a['id']}/gedcom/stage",json={'text':'0 HEAD\n0 @I1@ INDI\n1 NAME Imported /Person/\n0 TRLR'}).json(); assert staged['people']==1
    exported=client.get(f"/v1/families/{a['id']}/gedcom/export").text; assert '0 HEAD' in exported
    audit=client.get(f"/v1/families/{a['id']}/audit").json(); assert len(audit)>=4

def test_ui_contract():
    page=client.get('/').text
    for label in ['Family Tree','People','Families','Encoder','Ancestry/DNA','Records','Timeline','Search','Administration']:
        assert label in page
    assert 'viewport' in page


def test_interactive_workspace_contract():
    page=client.get('/').text
    for marker in [
        'id="familySelect"', 'id="personSelect"', 'id="treeCanvas"',
        'id="familyName"', 'id="personName"', 'id="relationshipType"',
        'id="encodeButton"', 'function createFamily', 'function addPerson',
        'function addRelationship', 'function runEncoder', 'function loadTree',
        "fetch('/v1/families'"
    ]:
        assert marker in page


def test_family_listing_endpoint_for_workspace():
    client.post('/v1/families',json={'name':'Alpha'})
    client.post('/v1/families',json={'name':'Beta'})
    r=client.get('/v1/families')
    assert r.status_code == 200
    assert [x['name'] for x in r.json()] == ['Alpha','Beta']
