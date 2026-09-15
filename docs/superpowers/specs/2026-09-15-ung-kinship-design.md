# UNG-KINSHIP System Design

**Status:** Approved architecture, written specification for implementation review  
**Date:** 2026-09-15

## Purpose
UNG-KINSHIP is a multi-family genealogy, family-tree, and family-encoding platform. It supports private authorized family workspaces while allowing many independent families to maintain their own trees. It records living and deceased people, complex family relationships, ancestry records, and optional DNA/genetic ancestry information.

## Identity and Encoding
Every family receives a permanent family identifier such as `FAM-00482`.

Every person receives two identifiers:
- Permanent member ID: `FAM-00482-001`. This is immutable and remains stable when relationships, names, households, or lineage interpretations change.
- Human-readable lineage code: `00482-G03-B02-017`, representing family, generation, branch, and member position. This is derived genealogy metadata and may be recalculated when the tree is corrected.

Visible identifiers must not encode DNA data, health data, dates of birth, government identifiers, or other sensitive personal information.

## Family and Person Registry
The registry stores families and people independently from user accounts. A deceased ancestor or other person represented in the tree does not need an account. Person records support names, aliases, life dates, living/deceased status, biography, photographs, documents, important events, and source references.

Accounts may be linked to person records when appropriate, but account identity and genealogy identity remain separate concepts.

## Relationship Graph
The authoritative relationship model supports biological parent/child, adoptive parent/child, guardian/ward, spouse/partner, former spouse/partner, step-family, siblings, half-siblings, twins, and unknown or disputed parentage. Relationships carry type, status, effective dates when known, provenance, and visibility controls.

The graph supports unlimited ancestor and descendant traversal, multiple family branches, multiple marriages/partnerships, common-ancestor discovery, and branch switching.

The system rejects impossible graph cycles and detects potential duplicates and contradictory relationship data. Disputed or uncertain genealogy may be represented explicitly rather than silently overwriting prior claims.

## Family Encoder
The encoder assigns permanent IDs transactionally and derives lineage codes from the accepted relationship graph. Permanent IDs never change. Lineage-code recalculation preserves an audit record of prior derived codes.

The encoder validates uniqueness, family membership, generation assignment, branch assignment, duplicate candidates, and graph integrity before accepting a change.

## User Experience
The primary navigation contains Family Tree, People, Families, Encoder, Ancestry/DNA, Records, Timeline, Search, and Administration.

The interactive tree supports ancestor and descendant expansion, branch navigation, relationship highlighting, generation indicators, and person selection. Selecting a person opens a profile with parents, siblings, partners, children, ancestors, descendants, records, and timeline events subject to permissions.

The interface is responsive for phones, tablets, and desktop computers.

## Records and Timeline
Families can attach records and source references to people and relationships. Events such as birth, death, marriage, adoption, migration, and other family milestones appear on a chronological timeline. Every substantive genealogy edit records who made it, when it was made, and what changed.

## DNA and Ancestry
DNA/genetic ancestry information is optional and private by default. It is stored separately from public genealogy fields and protected by additional authorization checks. The system records consent/provenance for genetic information and allows access to be revoked without deleting the person's genealogy identity.

DNA information is never included in permanent IDs or lineage codes.

## Privacy and Authorization
Each family is an isolated workspace. Baseline roles are family owner, administrator, editor, contributor, and viewer. Authorization is checked at the family boundary and again for specially protected records such as DNA information.

Public sharing is disabled by default. Living-person information receives stricter defaults than ordinary historical/deceased-person records. Sensitive actions and access-control changes are auditable.

## Interoperability
The system supports GEDCOM import and export. Imports are validated and staged before changing the authoritative tree. Duplicate detection and relationship validation run before commit. Exports honor the requesting user's permissions and privacy restrictions.

## Architecture
The application uses a FastAPI service layer and PostgreSQL as the authoritative transactional store. Genealogy relationships are modeled as graph-friendly relational edges so PostgreSQL remains the source of truth while recursive traversal services provide graph behavior. A separate graph database is not required for Version 1; this avoids dual-write consistency problems while preserving a migration path if future scale requires one.

The web client consumes versioned REST APIs. Domain modules separate family registry, person registry, relationship graph, encoding, tree traversal, records/timeline, ancestry/DNA, authorization, audit, and GEDCOM processing.

## Security Baseline
Use authenticated sessions/tokens, server-side authorization, least-privilege roles, encrypted transport, protected secrets, parameterized database access, input validation, rate limiting for abuse-prone endpoints, secure upload validation, and immutable/auditable security events. Sensitive genetic records require explicit authorization beyond ordinary tree viewing.

## Version 1 Build Groups
Group 1 delivers family/person identity, relationship storage and validation, permanent ID generation, lineage encoding, PostgreSQL persistence, and API tests.

Group 2 delivers the responsive interactive tree, profiles, search, records, timeline, genealogy traversal, duplicate detection, and administrative family-management UI.

Group 3 delivers ancestry/DNA controls, GEDCOM import/export, privacy hardening, audit review, security testing, and complete end-to-end acceptance testing.

## Acceptance Criteria
A Version 1 acceptance run must demonstrate: creating two isolated families; registering living and deceased people; building at least four generations; representing biological, adoptive, guardian, spouse, former-spouse, step, and half-sibling relationships; generating immutable member IDs and derived lineage codes; correcting a relationship without changing permanent IDs; rejecting a relationship cycle; finding ancestors and descendants; enforcing cross-family isolation; protecting DNA records; importing and exporting a representative GEDCOM dataset; and preserving an auditable history of genealogy and permission changes.
