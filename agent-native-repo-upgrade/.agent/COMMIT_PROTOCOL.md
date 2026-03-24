# COMMIT PROTOCOL
# Run through this checklist after completing EVERY task.
# Stale metadata costs the next agent 5–10 extra tool calls. Don't skip this.

---

## After ANY code change

### 1. FILES.yaml
- Did you **add** a new source file?
  → Add a new entry with: `what`, `exports`, `reads_from`, `writes_to`, `before_editing`
- Did you **significantly change** an existing file's behavior?
  → Update its `what`, `writes_to`, or `before_editing` entry
- Did you **delete** a file?
  → Remove its entry

### 2. ROUTES.yaml
- Did you **add a new route** in `src/app.ts`?
  → Add entry with: handler path#function, auth_required, middleware, capability, tests
- Did you **remove or rename** a route?
  → Update or remove the entry

### 3. MANIFEST.yaml
- Did you **add a new capability** (new handler)?
  → Add entry with: description, handler, contract, side_effects, dependencies, tests
- Did you **change side effects** of an existing capability?
  → Update its `side_effects` field

### 4. INVARIANTS.md
- Did you **fix a known violation**?
  → Change `CURRENT STATUS: VIOLATED` to `CURRENT STATUS: RESOLVED`
  → Add `RESOLVED_IN: <file>` line
- Did you **discover a new constraint**?
  → Add a new `INV-XXX` entry with WHAT, WHY, HOW, TEST, NEVER

### 5. IMPACT_MAP.yaml
- Did you **create a new dependency** between files?
  → Add the dependency to the relevant file entries
- Did you **change the interface** of `src/_shared/db.ts`?
  → Update every file that imports from it

### 6. CONCEPTS.yaml
- Did you **implement something** that was listed as `NOT IMPLEMENTED`?
  → Update `status` and add `primary_files`
- Did you **add a new domain concept**?
  → Add an entry

### 7. CHANGELOG.agent.yaml
**Always append an entry.** Even for small changes.

```yaml
- date: YYYY-MM-DD
  task: "<one-line description of what you were asked to do>"
  files_modified:
    - path/to/file.ts
  files_created:
    - path/to/new/file.ts
  capabilities_added: []
  capabilities_modified: []
  invariants_resolved: []
  invariants_introduced: []
  metadata_updated: [FILES.yaml, ROUTES.yaml]  # list what you updated
```

---

## Quick decision tree

```
Added new file?           → FILES.yaml + (MANIFEST if handler) + (ROUTES if route)
Added new route?          → ROUTES.yaml + FILES.yaml(app.ts) + MANIFEST.yaml
Fixed INV-XXX?            → INVARIANTS.md + FILES.yaml(before_editing of fixed file)
Changed db.ts interface?  → IMPACT_MAP.yaml + FILES.yaml(db.ts)
Implemented new concept?  → CONCEPTS.yaml
Any of the above?         → CHANGELOG.agent.yaml (always)
```
