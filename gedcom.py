import re
from traversal import find_duplicate_candidates
from services import register_person

def stage_gedcom_import(text):
    if '0 HEAD' not in text or '0 TRLR' not in text: raise ValueError('invalid GEDCOM')
    names=re.findall(r'^1 NAME (.+)$',text,re.M)
    return {'valid':True,'people':names,'warnings':[]}
def commit_staged_import(db,family_id,stage):
    created=[]; warnings=[]
    for name in stage['people']:
        clean=name.replace('/','').strip()
        if find_duplicate_candidates(db,family_id,clean): warnings.append({'name':clean,'warning':'duplicate candidate'}); continue
        created.append(register_person(db,family_id,clean,False))
    return {'created':created,'warnings':warnings}
def export_gedcom(people):
    lines=['0 HEAD','1 SOUR UNG-KINSHIP']
    for p in people: lines += [f'0 @I{p.id}@ INDI',f'1 NAME {p.name}']
    lines.append('0 TRLR'); return '\n'.join(lines)
