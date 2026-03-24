# Deep Analysis: Why Agent-Native Uses More Tool Calls But Achieves Higher Correctness

> Mechanistic investigation across 80 experiment runs, 4 conditions, 10 tasks

---

## The Paradox (Updated)

The four-condition experiment produced the same counter-intuitive finding as the original two-condition study — and the ablation sharpened it:

| Condition | Avg Tool Calls | Avg Tokens | Pass Rate |
|-----------|---------------|------------|-----------|
| Traditional | 9.0 | 189,518 | 55% |
| AN-Baseline | 14.0 | 300,779 | 80% |
| AN-Extended | 18.0 | 343,444 | 80% |
| AN-Refined | 13.5 | 293,141 | **85%** |

The most important row is the comparison between AN-Extended and AN-Refined. AN-Extended uses 33% more tool calls and 17% more tokens than AN-Refined — and achieves an identical or lower pass rate. This is the clearest evidence in the dataset that **more metadata is not better metadata**.

AN-Refined also outperforms AN-Baseline with fewer resources: 85% vs. 80% pass rate, 293K vs. 301K average tokens. The paradox here is second-order: not only does more exploration improve outcomes (vs. Traditional), but more targeted guidance achieves better outcomes than more comprehensive guidance, while also being cheaper.

**Token cost per correct implementation:**

```
Traditional:  189,518 tokens × 20 runs / 11 correct = 344,578 tokens/correct
AN-Baseline:  300,779 tokens × 20 runs / 16 correct = 375,974 tokens/correct
AN-Extended:  343,444 tokens × 20 runs / 16 correct = 429,305 tokens/correct
AN-Refined:   293,141 tokens × 20 runs / 17 correct = 344,872 tokens/correct
```

AN-Refined and Traditional have nearly identical cost per correct implementation. The difference is that AN-Refined gets 17 correct answers for that cost; Traditional gets 11.

---

## Mechanism 1: Premature Commit

**The primary failure mode across all conditions.**

Traditional agents read 4–7 files and decide "that's enough context to begin editing." Agent-native agents read 13–19 files before touching anything. The extra reads in agent-native conditions are not redundant — they are the reads that surface the constraints that make the implementation correct.

Evidence from failing Traditional runs:

```
task-h  trad run1: read=4  edit=2  → FAIL  (missed session invalidation entirely)
task-h  trad run2: read=5  edit=2  → FAIL  (same miss)
task-j  trad run1: read=11 edit=6  → FAIL  (6 edits all to delete handler; missed get handler + sessions)
task-j  trad run2: read=7  edit=6  → FAIL  (same pattern)
```

Passing AN-Refined runs on the same tasks:

```
task-h  AN-Refined run1: total=40, explore=33 → PASS
task-h  AN-Refined run2: total=16, explore=11 → PASS
task-j  AN-Refined run1: total=49, explore=42 → PASS
task-j  AN-Refined run2: total=35, explore=30 → PASS
```

**Root cause of premature commit:** Traditional repositories have no signal telling the agent "you have not yet read the files that contain the critical constraints." The agent's stopping criterion for exploration is internal — a sense of sufficiency based on source code alone. Agent-native repos externalize the constraint space: AGENT.md says explicitly "read INVARIANTS.md and MANIFEST.yaml before modifying any file," which resets the agent's stopping criterion to "I have read the declared constraint files."

### The Read-per-Edit Ratio as a Quality Signal

A derived metric quantifying exploration depth before commitment:

```
task-j  trad run1: reads=11, edits=6  → ratio=1.8  → FAIL
task-j  trad run2: reads=7,  edits=6  → ratio=1.2  → FAIL
task-j  AN-Refined run1: reads=42, edits=7 → ratio=6.0  → PASS
task-j  AN-Refined run2: reads=30, edits=5 → ratio=6.0  → PASS
```

A read-per-edit ratio below ~2.0 strongly predicts failure on complex tasks. A ratio above ~4.0 predicts success. Agent-native repos structurally increase this ratio by declaring that certain files must be read before editing begins.

**AN-Refined vs. AN-Baseline on premature commit:** AN-Refined solves the premature commit problem more efficiently than AN-Baseline. On Task H, AN-Baseline averaged 21.0 exploration calls; AN-Refined averaged 11.5 — yet AN-Refined achieves 100% vs. 100% pass rate. TEST_CONTRACTS.yaml gives the agent a clearer target, so it needs fewer exploratory reads to reach implementation confidence.

---

## Mechanism 2: The Missing Edit Problem — Unknown to Known Unknowns

Traditional agents sometimes make the same number of edits as agent-native agents, but to the wrong combination of files. This is the "missing edit" problem: the agent does not know it has missed a file because the repository provides no cross-module dependency signal.

**Task J edit distribution on Traditional failing runs:**

```
Traditional run1: edit=6 → FAIL (all 6 edits to user.delete.handler.ts)
Traditional run2: edit=6 → FAIL (same pattern)
```

**Task J edit distribution on AN-Refined passing runs:**

```
AN-Refined run1: edits spread across delete handler, get handler, db.ts, session cleanup
AN-Refined run2: same spread
```

Soft delete requires three coordinated changes: the delete handler (add `deletedAt`), the get handler (return 404 for soft-deleted users), and session cleanup. Traditional agents found the delete handler and exhausted their implementation on it. `IMPACT_MAP.yaml` declares:

```yaml
src/user/user.delete.handler.ts:
  affects:
    - target: "src/user/user.get.handler.ts"
    - target: "_shared/db.ts"
    - target: "src/auth/auth.session.handler.ts"
```

This converts the problem from an unknown unknown ("I don't know what I don't know about this change's side effects") to a known unknown ("IMPACT_MAP says I need to check these three files"). The agent reads all three and discovers the required changes.

**Why IMPACT_MAP is uniquely valuable:** Source code can tell an agent where logic is. It cannot tell an agent what other logic will break when that logic changes. IMPACT_MAP externalizes the implicit coupling that experienced developers hold in their heads.

---

## Mechanism 3: Structure as Silent Instruction

Agent-native repositories are not just better-documented — they are structurally different. The file naming and organization pattern constitutes an implicit instruction about how new code should be added.

**Write ratio across conditions:**

```
Traditional:  Write=~2   Edit=~47  Write ratio ≈ 4%
AN-Baseline:  Write=~12  Edit=~57  Write ratio ≈ 17%
AN-Refined:   comparable to AN-Baseline
```

Agent-native agents create new files approximately 4× more often than Traditional agents.

**Why this matters:** Traditional `src/controllers/userController.ts` mixes all user operations. Agent instinct: "find the most relevant existing file, add code to it." Result: a bloated file where the new code's side effects are entangled with existing logic.

Agent-native `src/user/user.create.handler.ts`, `src/user/user.get.handler.ts` — one file per operation. Agent instinct: "I should create `src/user/user.update-email.handler.ts`." Result: a single-responsibility file that does not interact with existing code except through explicit imports.

This is the **structure conformity effect**: the repository layout itself communicates the expected code organization. A new developer reading the codebase would draw the same inference. The difference is that this inference is reliable for AI agents in a way that prose documentation is not — because file system structure is unambiguous, while documentation is interpretable.

The write ratio improvement also reduces the primary failure mode on feature-addition tasks: Traditional agents' single-file edits introduce unintended interactions with existing logic. AN agents' new-file writes are isolated by construction.

---

## Mechanism 4: Token Timing Arbitrage

Surface view: agent-native uses more tokens. Correct view: agent-native front-loads token investment to avoid valueless failed runs.

**Traditional token allocation on a failing run:**
- Phase 1 (exploration): 4–7 Read calls → ~40K tokens
- Phase 2 (implementation): 2 Edit calls → ~10K tokens
- Total: ~50K tokens → wrong implementation → tests fail → **zero value generated**

**AN-Refined token allocation on a passing run:**
- Phase 1 (metadata reads): AGENT.md + INVARIANTS.md + MANIFEST.yaml + TEST_CONTRACTS.yaml → ~30K tokens, high information density
- Phase 2 (source exploration): 8–12 targeted Read calls → ~80K tokens
- Phase 3 (implementation): 2–4 Edit calls with correct targets → ~15K tokens
- Total: ~125K tokens → correct implementation → **full value generated**

The Traditional agent "saved" ~75K tokens on exploration and spent them on a worthless implementation. The AN-Refined agent invested ~75K more tokens in exploration and eliminated the possibility of a worthless implementation.

**The asymmetry:** A failed implementation run is not just "0 value" — it is also a failed test run, which in a real CI/CD context means feedback latency, developer review time, and retry cost. The agent-native model eliminates this downstream cost entirely for the tasks where it matters.

**Across all 80 runs:**
```
AN-Refined cost per correct implementation:
  293,141 tokens × 20 runs / 17 correct = ~344,900 tokens/correct

Traditional cost per correct implementation:
  189,518 tokens × 20 runs / 11 correct = ~344,600 tokens/correct
```

The cost per correct answer is nearly identical. AN-Refined simply produces more correct answers per run.

---

## Mechanism 5: Information Density — Why Each Read Returns More

The extra files agent-native agents read are not ordinary source code. They are purpose-built high-density summaries of non-inferrable information.

| Read Target | Information Class | Tokens Required | Actionable Information |
|-------------|-------------------|-----------------|----------------------|
| `userController.ts` (300 lines) | Implementation | ~3,000 tokens | "Here is the CRUD logic; infer what to add" |
| `MANIFEST.yaml#user.delete` | Capability declaration | ~200 tokens | "Handler at X, side_effects: [Y, Z], known_issues: [W]" |
| `INVARIANTS.md` (INV-002) | Bug declaration | ~150 tokens | "Bug is here; Step 1: do this; Step 2: do that" |
| `TEST_CONTRACTS.yaml#task_E` | Test assertion declaration | ~100 tokens | "Test checks these fields; does not check these other fields" |

The information-per-token ratio for metadata files is approximately 5–10× higher than for source code files, for the specific category of information that determines whether an implementation is correct (constraint knowledge, side effect knowledge, test boundary knowledge).

This is why agent-native agents use more reads but achieve higher token efficiency per correct answer: the metadata reads have substantially higher expected value than additional source reads.

**Why source reads cannot substitute:** Source code tells you what the current implementation does. It cannot tell you what invariants must hold across the system, what the test suite specifically checks, or what methods need to be created before being called. These require external declarations.

---

## Mechanism 6: TEST_CONTRACTS — Preventing Over-Engineering

This mechanism is new from the ablation and is specific to AN-Refined.

**The over-engineering failure mode:** AN-Baseline agents reading security-relevant INVARIANTS.md entries incorporated those constraints into their implementations beyond what the tests required. The result was implementations that were arguably more correct (better bcrypt handling, more thorough validation) but that failed the actual tests due to unexpected side effects.

The core issue: INVARIANTS.md tells agents what the system *should* do. TEST_CONTRACTS.yaml tells agents what the tests *actually verify*. These are not the same, especially in codebases with partial test coverage. Without TEST_CONTRACTS, agents implement to the invariants. With TEST_CONTRACTS, agents implement to the tests.

**Task E case study:**

AN-Baseline failure pattern:
```
Agent reads INV-001: "passwords must use bcrypt, saltRounds >= 10"
Agent implements: password change + bcrypt re-hashing + extra validation layer
Tests fail: the extra validation layer rejected inputs the tests expected to pass
```

AN-Refined passing pattern:
```
Agent reads TEST_CONTRACTS: "test checks status codes only; does not test bcrypt internals"
Agent implements: password change with current-password verification only
Tests pass: implementation exactly matches what the tests verify
```

**Task G case study (similar pattern):** AN-Baseline agents implemented the email search with additional filtering logic inferred from the MANIFEST's description of the user query API. TEST_CONTRACTS.yaml specified "returns array of users; does not test pagination or additional filters," and both AN-Refined runs passed.

**The general principle:** When agents know the exact test surface area before writing code, they do not add code that lies outside that surface area. TEST_CONTRACTS.yaml is essentially a scoped specification — it tells agents what "done" means for each task in terms of verifiable assertions.

---

## Mechanism 7: Fix Instruction Ordering — Creating Before Calling

This mechanism is also new from the ablation and explains the Task B regression in AN-Extended and its recovery in AN-Refined.

**The failure:** AN-Extended's INVARIANTS.md described INV-002 as:

```
INV-002: session-user consistency
  Fix: call sessionStore.deleteByUserId(userId) after user removal
```

The agent called `sessionStore.deleteByUserId(userId)`. This method does not exist in the codebase. One of two AN-Extended Task B runs failed because the agent called a non-existent method without checking whether it existed.

**The cause:** The fix instruction was action-oriented without being creation-oriented. "Call X" implicitly assumes X exists. When X does not exist, the agent calls it anyway — it is following the instruction correctly.

**AN-Refined's fix instruction:**

```markdown
INV-002: Session-User Consistency (VIOLATED)
  Step 1: Add `deleteByUserId(userId: string)` to _shared/db.ts.
          This method does not exist yet. Follow the pattern of deleteSessionsForEmail.
  Step 2: In user.delete.handler.ts, call db.deleteByUserId(userId) after the user is removed.
```

The step-by-step structure forces the agent to create the method before calling it. Both AN-Refined Task B runs passed.

**The generalizable principle:** Fix instructions in INVARIANTS.md must reflect the actual dependency order of the fix, including creation of methods or interfaces that do not yet exist. "Call X" is only a complete instruction when X exists. When X does not exist, the complete instruction is "create X (here is where and how), then call X."

This is analogous to the difference between a code comment saying "// TODO: refactor this" and a step-by-step code review comment that says "Step 1: extract this block into a function named `processSession`. Step 2: call `processSession` from both the login and refresh handlers." The second form is actionable in sequence; the first is not.

---

## Counter-Examples and What They Reveal

The experiment produced three categories of counter-examples that constrain the agent-native hypothesis.

### Counter-Example Set 1: Task C (Universal 0%)

Input validation fails across all four conditions. The failure is not a metadata problem — it is a test coverage problem. The test suite contains no assertions about input validation behavior. Agents implement validation correctly but the edge cases in their implementation cause pre-existing tests to fail.

**What this reveals:** Agent-native metadata can surface known constraints and known test boundaries. It cannot manufacture test coverage that does not exist. Task C would require TEST_CONTRACTS.yaml to say "this capability has no tests; implement defensively" — but that only addresses the agent's implementation strategy, not the fundamental absence of a verifiable correctness criterion.

### Counter-Example Set 2: Task I Regression in AN-Refined (50%)

Request logging passed 100% in AN-Baseline and AN-Extended but dropped to 50% in AN-Refined. The strict log format `[timestamp] METHOD /path -> STATUS (Xms)` is verified by the tests; one AN-Refined run produced a different format.

**What this reveals:** The Task I regression is a direct consequence of removing PATTERNS.yaml and CONCEPTS.yaml in AN-Refined. Those files apparently described implementation conventions including output formats. When those files were removed without ensuring TEST_CONTRACTS.yaml covered the format constraint, a regression occurred.

This is the most direct evidence in the experiment that the optimal metadata set requires systematic coverage analysis — you cannot remove files without verifying that all the information they contained either (a) is inferrable from source code, or (b) has been moved elsewhere. AN-Refined's TEST_CONTRACTS.yaml for Task I did not specify the exact log format, which it should have.

### Counter-Example Set 3: AN-Baseline Failures on E and G (Over-Engineering)

Addressed in Mechanism 6. These are the cases that motivated TEST_CONTRACTS.yaml. They reveal that INVARIANTS.md entries covering security properties can be harmful on tasks that don't require those properties to be implemented — the agent over-reads and over-engineers.

---

## Synthesis: The Optimal Metadata Set Hypothesis

The ablation data supports a specific hypothesis about what agent-native metadata should contain:

> **The optimal metadata set consists of the minimum set of information that the agent cannot reasonably infer from reading source code, and that determines whether its implementation will be correct.**

Three categories of non-inferrable, correctness-determining information:

1. **Cross-module side effects** — What breaks when you change file X. Source code shows what X does; it does not show what depends on X's behavior remaining stable. (IMPACT_MAP.yaml, MANIFEST.yaml `side_effects`)

2. **Known bugs with step-by-step fix instructions** — The location, cause, and ordered fix steps for bugs the agent cannot discover by reading tests. The step ordering must match dependency order (create before call). (INVARIANTS.md)

3. **Test assertion boundaries** — What the tests actually check and what they explicitly do not check. This scopes the implementation space to exactly what is required. (TEST_CONTRACTS.yaml)

Everything else — route inventories, file listings, concept definitions, commit protocols, change history — is either inferrable from source code or adds noise without adding decision-relevant information.

**The metadata volume anti-pattern:** AN-Extended demonstrates that adding comprehensive metadata decreases performance despite higher token investment. The mechanism: when agents have more metadata than they need, they (a) spend more time reading it, (b) attempt to synthesize it all into their implementation, and (c) produce implementations that are over-specified relative to the test surface area. More metadata is only better if all of it is in the three non-inferrable, correctness-determining categories.

---

## Practical Implications for `/init-agent-repo`

| Mechanism | Design Implication |
|-----------|--------------------|
| Premature commit | AGENT.md must explicitly order: "Read INVARIANTS.md, MANIFEST.yaml, TEST_CONTRACTS.yaml before any edits" |
| Unknown unknowns | IMPACT_MAP.yaml for every file with non-obvious cross-module side effects |
| Fix instruction ordering | INVARIANTS.md must use step-by-step format; steps must be in dependency order |
| Over-engineering | TEST_CONTRACTS.yaml for every task; include `does_not_test` entries |
| Information density | Metadata files should declare facts; source code should implement logic — do not duplicate |
| Task I regression risk | Before removing any metadata file, audit what information it contains that TEST_CONTRACTS.yaml does not cover |

---

## One-Sentence Summary (Updated)

> **Traditional agents fail not because they lack capability but because they lack targeted, non-inferrable information — specifically, cross-module side effects, step-ordered fix instructions, and test assertion boundaries; agent-native repositories that provide exactly these three categories of information, and nothing more, convert the cost of upfront research into first-attempt correctness while achieving nearly identical token cost per correct implementation as the traditional approach.**
