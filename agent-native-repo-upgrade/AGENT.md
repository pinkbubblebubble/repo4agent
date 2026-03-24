# AGENT ENTRY POINT — v2

> **Protocol:** Read `.agent/COMMIT_PROTOCOL.md` BEFORE starting any task.
> Update metadata AFTER completing any task. Stale metadata is worse than no metadata.

---

## Quick Orient

| Key | Value |
|-----|-------|
| Stack | TypeScript · Express.js · Jest |
| Entry | `src/app.ts` |
| Test | `npm test` |
| Data | In-memory Maps (no external DB) |

---

## Step 1 — Find What You Need (zero grep needed)

| You want to… | Go to |
|---|---|
| Find a specific file | `.agent/FILES.yaml` |
| Find a route's handler | `.agent/ROUTES.yaml` |
| Find all files related to a concept (auth, sessions…) | `.agent/CONCEPTS.yaml` |
| Find which capability to modify | `.agent/MANIFEST.yaml` |
| Know what constraints exist | `.agent/INVARIANTS.md` |
| Know what a change will break | `.agent/IMPACT_MAP.yaml` |
| Know what was changed recently | `.agent/CHANGELOG.agent.yaml` |

---

## Step 2 — Before You Edit

1. Read `.agent/INVARIANTS.md` — non-negotiable constraints
2. Check `.agent/FILES.yaml` → the target file's `before_editing` block
3. Check `.agent/IMPACT_MAP.yaml` → what your target file affects

---

## Step 3 — After You Edit (mandatory)

Follow `.agent/COMMIT_PROTOCOL.md` exactly.
Skipping this makes the metadata stale for the next agent.

---

## Capability Index

| Capability | Handler | Tests |
|---|---|---|
| user.create | `src/user/user.create.handler.ts` | `src/user/user.test.ts#create` |
| user.get | `src/user/user.get.handler.ts` | `src/user/user.test.ts#get` |
| user.update | `src/user/user.update.handler.ts` | `src/user/user.test.ts#update` |
| user.delete | `src/user/user.delete.handler.ts` | `src/user/user.test.ts#delete` |
| user.list | `src/user/user.list.handler.ts` | `src/user/user.test.ts#list` |
| auth.login | `src/auth/auth.login.handler.ts` | `src/auth/auth.test.ts#login` |
| auth.logout | `src/auth/auth.logout.handler.ts` | `src/auth/auth.test.ts#logout` |

## Known Issues

- **INV-002**: `user.delete` does not invalidate active sessions → `src/user/user.delete.handler.ts`
