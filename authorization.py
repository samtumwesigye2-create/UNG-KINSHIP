from sqlalchemy import select
from models import FamilyRole
ROLES=('owner','administrator','editor','contributor','viewer')
RANK={r:i for i,r in enumerate(reversed(ROLES))}
def grant_role(db,family_id,subject,role,protected_access=False):
    if role not in ROLES: raise ValueError('invalid role')
    grant=db.scalar(select(FamilyRole).where(FamilyRole.family_id==family_id,FamilyRole.subject==subject))
    if grant: grant.role=role; grant.protected_access=protected_access
    else: grant=FamilyRole(family_id=family_id,subject=subject,role=role,protected_access=protected_access); db.add(grant)
    db.commit(); return grant
def require_family_access(db,family_id,subject,minimum='viewer',protected=False):
    grant=db.scalar(select(FamilyRole).where(FamilyRole.family_id==family_id,FamilyRole.subject==subject))
    if not grant or RANK[grant.role] < RANK[minimum] or (protected and not grant.protected_access): raise PermissionError('access denied')
    return grant
