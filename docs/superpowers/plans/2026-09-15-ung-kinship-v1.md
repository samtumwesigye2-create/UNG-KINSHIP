# UNG-KINSHIP V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved UNG-KINSHIP Version 1 genealogy, family-tree, and dual family-encoding platform.

**Architecture:** FastAPI exposes versioned REST APIs backed by PostgreSQL. Families, people, relationships, identifiers, records, permissions, DNA metadata, and audit events are relational source-of-truth records; recursive traversal services provide graph behavior without a second graph database.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, PostgreSQL, Alembic, pytest, httpx, responsive HTML/CSS/JavaScript web client.

**Spec:** `docs/superpowers/specs/2026-09-15-ung-kinship-design.md`

## Global Constraints
- Permanent member IDs are immutable and formatted `FAM-#####-###`.
- Lineage codes are derived and formatted `#####-G##-B##-###`.
- Visible identifiers never encode DNA, health, birth dates, or government identifiers.
- PostgreSQL is the Version 1 source of truth; no separate graph database.
- Family workspaces are isolated; public sharing is disabled by default.
- DNA/genetic ancestry is optional, private by default, and requires additional authorization.
- Living-person records receive stricter privacy defaults than deceased-person records.
- Every substantive genealogy or permission change is auditable.
- Implementation follows test-first RED → GREEN → REFACTOR cycles; no production behavior is added without a failing test first.

---

## File Map
- `app.py` — FastAPI application assembly and `/health` endpoint.
- `database.py` — engine/session configuration and transaction boundary.
- `models.py` — SQLAlchemy family, person, relationship, identifier, audit, record, DNA, and permission entities.
- `schemas.py` — Pydantic request/response contracts.
- `family_registry.py` — family creation and family identifier allocation.
- `person_registry.py` — living/deceased person registration and immutable member ID allocation.
- `relationships.py` — relationship creation, validation, provenance, uncertainty, and cycle prevention.
- `encoder.py` — generation/branch derivation and lineage-code history.
- `traversal.py` — ancestors, descendants, common ancestors, and branch traversal.
- `authorization.py` — family role and protected-record authorization.
- `records.py` — documents/source metadata and timeline events.
- `dna.py` — separately authorized ancestry/DNA metadata and consent/provenance.
- `gedcom.py` — staged GEDCOM import and privacy-aware export.
- `audit.py` — append-only genealogy/security event recording.
- `static/index.html`, `static/app.js`, `static/styles.css` — responsive family-tree application.
- `tests/` — domain and API acceptance tests.
- `.github/workflows/ci.yml` — automated pytest verification.

### Task 1: Application, persistence, and family registry
**Files:** Create `app.py`, `database.py`, `models.py`, `schemas.py`, `family_registry.py`, `tests/test_family_registry.py`, `requirements.txt`, `.github/workflows/ci.yml`.

**Interfaces:** `create_family(session, name: str) -> Family`; family code allocator returns `FAM-#####` and is transactionally unique.

- [ ] Write failing tests proving two families receive distinct identifiers and `/health` returns `{"status":"ok"}`.
- [ ] Run `pytest tests/test_family_registry.py -v`; expected RED because application/domain modules do not exist.
- [ ] Implement the minimum database models, transaction/session layer, family allocator, FastAPI health/family endpoints.
- [ ] Run the test again; expected PASS.
- [ ] Refactor without changing behavior, run full `pytest -q`, then commit `feat: add family registry foundation`.

### Task 2: Person registry and permanent member IDs
**Files:** Create `person_registry.py`, `tests/test_person_registry.py`; modify `models.py`, `schemas.py`, `app.py`.

**Interfaces:** `register_person(session, family_id, names, living: bool, life_dates=None) -> Person`; allocator returns `FAM-#####-###` and never mutates an existing member ID.

- [ ] Write failing tests for living people, deceased ancestors without accounts, sequential unique member IDs, and immutability after profile edits.
- [ ] Run `pytest tests/test_person_registry.py -v`; expected RED for missing registry behavior.
- [ ] Implement minimum person model, allocator, profile update, and API routes.
- [ ] Run targeted and full tests; expected PASS.
- [ ] Commit `feat: add immutable family member identities`.

### Task 3: Relationship graph and integrity validation
**Files:** Create `relationships.py`, `tests/test_relationships.py`; modify `models.py`, `schemas.py`, `app.py`.

**Interfaces:** `add_relationship(session, family_id, source_id, target_id, relationship_type, status, provenance=None) -> Relationship`; supported types cover biological/adoptive parent-child, guardian, spouse/partner, former spouse/partner, step-family, sibling, half-sibling, twin, unknown/disputed parentage.

- [ ] Write failing tests for supported relationships, cross-family rejection, disputed claims, and parent/child cycle rejection.
- [ ] Run targeted tests; expected RED because graph validation is absent.
- [ ] Implement relationship edges and cycle detection using recursive traversal against authoritative PostgreSQL records.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: add validated genealogy relationship graph`.

### Task 4: Dual family encoder
**Files:** Create `encoder.py`, `tests/test_encoder.py`; modify `models.py`, `schemas.py`, `app.py`.

**Interfaces:** `encode_lineage(session, family_id) -> list[LineageAssignment]`; codes follow `#####-G##-B##-###`; prior derived codes are retained as history.

- [ ] Write failing tests for four generations, multiple branches, deterministic codes, recalculation after corrected parentage, and permanent-ID stability.
- [ ] Run targeted tests; expected RED because encoder is missing.
- [ ] Implement generation/branch calculation and transactional lineage history.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: add lineage encoder`.

### Task 5: Authorization and audit foundation
**Files:** Create `authorization.py`, `audit.py`, `tests/test_authorization.py`, `tests/test_audit.py`; modify `models.py`, `app.py`.

**Interfaces:** roles are `owner`, `administrator`, `editor`, `contributor`, `viewer`; `require_family_access(...)`; `record_audit_event(...)` appends immutable events.

- [ ] Write failing tests for family isolation, role restrictions, protected operations, and append-only audit events.
- [ ] Run targeted tests; expected RED.
- [ ] Implement role grants/checks and audit recording on genealogy/permission mutations.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: enforce family authorization and audit`.

### Task 6: Traversal, records, timeline, and duplicate detection
**Files:** Create `traversal.py`, `records.py`, `tests/test_traversal.py`, `tests/test_records.py`; modify `app.py`, `models.py`, `schemas.py`.

**Interfaces:** `ancestors(...)`, `descendants(...)`, `common_ancestors(...)`, `find_duplicate_candidates(...)`; timeline returns permission-filtered chronological events.

- [ ] Write failing tests for ancestor/descendant traversal, common ancestors, source attachments, timeline ordering, and duplicate candidates.
- [ ] Run targeted tests; expected RED.
- [ ] Implement minimum recursive traversal, records, timeline, and duplicate heuristics.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: add genealogy traversal and records`.

### Task 7: Responsive interactive family-tree client
**Files:** Create `static/index.html`, `static/app.js`, `static/styles.css`, `tests/test_web_ui.py`; modify `app.py`.

**Interfaces:** navigation exposes Family Tree, People, Families, Encoder, Ancestry/DNA, Records, Timeline, Search, Administration.

- [ ] Write failing HTTP/UI contract tests for navigation, person selection, tree data endpoint, and mobile viewport metadata.
- [ ] Run tests; expected RED.
- [ ] Implement responsive tree rendering, ancestor/descendant expansion, branch switching, relationship highlighting, and profile panel.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: add interactive family tree interface`.

### Task 8: DNA/ancestry privacy controls
**Files:** Create `dna.py`, `tests/test_dna_privacy.py`; modify `models.py`, `schemas.py`, `authorization.py`, `app.py`.

**Interfaces:** DNA records carry consent/provenance and require explicit protected-record permission beyond ordinary tree viewing.

- [ ] Write failing tests proving DNA is private by default, absent from identifiers/tree responses, accessible only with protected permission, and revocable without deleting genealogy identity.
- [ ] Run targeted tests; expected RED.
- [ ] Implement separate DNA storage/service authorization and consent revocation.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: protect ancestry and DNA records`.

### Task 9: GEDCOM interoperability
**Files:** Create `gedcom.py`, `tests/test_gedcom.py`; modify `app.py`.

**Interfaces:** `stage_gedcom_import(...)` validates without authoritative mutation; `commit_staged_import(...)` runs duplicate/relationship checks; `export_gedcom(...)` filters by permissions.

- [ ] Write failing tests for staged import, malformed relationship rejection, duplicate warning, committed import, and privacy-aware export.
- [ ] Run targeted tests; expected RED.
- [ ] Implement minimum GEDCOM parser/staging/commit/export behavior.
- [ ] Run targeted/full tests; expected PASS.
- [ ] Commit `feat: add GEDCOM import and export`.

### Task 10: V1 end-to-end acceptance and hardening
**Files:** Create `tests/test_v1_acceptance.py`; modify application files only for defects revealed by acceptance tests.

**Interfaces:** acceptance test exercises the public Version 1 REST/UI contracts.

- [ ] Write one failing acceptance scenario that creates two isolated families, registers living/deceased people, builds four generations, exercises biological/adoptive/guardian/spouse/former-spouse/step/half-sibling relationships, encodes lineage, corrects parentage without changing permanent IDs, rejects a cycle, traverses ancestors/descendants, protects DNA, imports/exports GEDCOM, and verifies audit history.
- [ ] Run `pytest tests/test_v1_acceptance.py -v`; fix only concrete acceptance failures using RED/GREEN cycles.
- [ ] Run `pytest -q`; expected all tests PASS.
- [ ] Verify no placeholder markers with `grep -R -n -E 'TODO|TBD|FIXME|pass$|NotImplemented' --exclude-dir=.git .`; expected no production placeholders.
- [ ] Commit `test: complete UNG-KINSHIP V1 acceptance`.

## Self-review
Spec coverage: all approved identity, relationship, encoding, privacy, tree, DNA, GEDCOM, audit, and acceptance requirements map to Tasks 1-10. Placeholder scan: no implementation placeholders are specified. Type consistency: family IDs, member IDs, lineage codes, roles, relationship services, traversal services, and GEDCOM staging interfaces use consistent names throughout the plan.
