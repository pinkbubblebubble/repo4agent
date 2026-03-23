# Deep Analysis: Why Agent-Native Uses More Tool Calls But Achieves Higher Correctness

> Data-driven investigation across 40 experiment runs

---

## The Paradox

The experiment produced a counter-intuitive result:

| | Traditional | Agent-Native | Change |
|--|------------|--------------|--------|
| Avg tool calls | 9.0 | 14.0 | +55.6% |
| Avg tokens | 189,518 | 300,779 | +58.7% |
| Test pass rate | 55% | **80%** | **+25pp** |

**More resources invested → better outcomes.** This is not an efficiency gain — it's a redistribution of where resources are invested within a task. Below is a layer-by-layer breakdown of the mechanism.

---

## Mechanism 1: Premature Commit

**The most critical finding.**

Look at how many files traditional agents read before failing:

```
task-a  trad run2: read=5  edit=2  → FAIL  (committed after only 5 reads)
task-b  trad run1: read=7  edit=2  → FAIL  (committed after only 7 reads)
task-h  trad run1: read=4  edit=2  → FAIL  (committed after only 4 reads)
task-h  trad run2: read=5  edit=2  → FAIL  (committed after only 5 reads)
task-j  trad run1: read=11 edit=6  → FAIL
task-j  trad run2: read=7  edit=6  → FAIL
```

Compare to agent-native passing runs on the same tasks:

```
task-h  AN  run1: read=19 edit=5   → PASS  (read 19 files before committing)
task-h  AN  run2: read=14 edit=4   → PASS
task-j  AN  run1: read=19 edit=5   → PASS
task-j  AN  run2: read=13 edit=7   → PASS
```

**The pattern is unmistakable**: traditional agents read 4-7 files and decide "that's enough," then commit to edits — which turn out to be wrong or incomplete. Agent-native agents read 13-19 files before touching anything, and their edits are correct.

**Root cause**: Traditional repos have no signal telling the agent "you haven't read the critical information yet." Agent-native repos' AGENT.md says at line 1: "Read .agent/INVARIANTS.md before touching anything" — forcing the agent to build complete context first.

### The Read-per-Edit Ratio

A derived metric that quantifies this behavior:

```
task-j  trad run1: ratio=1.8 r/e  → FAIL
task-j  trad run2: ratio=1.2 r/e  → FAIL
task-j  AN  run1:  ratio=3.8 r/e  → PASS
task-j  AN  run2:  ratio=1.9 r/e  → PASS
```

Agent-native agents read significantly more files per edit they make. They operate in "research-heavy before commit" mode. Traditional agents operate in "read a little, start editing" mode.

---

## Mechanism 2: The Missing Edit Problem

Traditional and agent-native agents sometimes make the same number of edits — but traditional agents edit the wrong combination of files.

**Task J (soft delete) edit distribution on passing runs:**

```
Traditional: edit=6 → FAIL  (6 edits all to the delete handler, repeatedly)
Agent-native: edit=5 → PASS  (5 edits to 5 different files)
```

Soft delete requires coordinated changes across three locations:
1. The delete handler (add `deletedAt` field)
2. The get handler (return 404 for soft-deleted users)
3. Session cleanup (invalidate sessions on soft delete)

The traditional agent found the delete handler and kept re-editing it. Agent-native's IMPACT_MAP.yaml declared "modifying `user.delete.handler.ts` affects user_store and session_store" — so the agent proactively found the other two files.

**Core insight**: Traditional agents don't know what they don't know (unknown unknowns). Agent-native's IMPACT_MAP converts unknown unknowns into known unknowns.

---

## Mechanism 3: The File Creation Pattern (Write Ratio)

```
Traditional:   Write=2   Edit=47   Write ratio = 4.1%
Agent-native:  Write=12  Edit=57   Write ratio = 17.4%
```

Agent-native agents create new files **4x more often** than traditional agents.

**Why this matters:**

Traditional repo's `src/controllers/userController.ts` mixes all user operations. When an agent adds a feature, its instinct is "find the most relevant file and add code to it" — resulting in a bloated file with co-located side effects.

Agent-native repo has `src/user/user.create.handler.ts`, `src/user/user.get.handler.ts`... one file per operation. When the agent sees this pattern, its instinct is "I should create `user.update-email.handler.ts`" — resulting in an isolated, single-responsibility file that doesn't disturb existing logic.

**Structure as convention**: The repository structure itself is a silent instruction to the agent.

---

## Mechanism 4: The True Token Efficiency

Surface-level, agent-native uses more tokens. Reframe the analysis:

```
Traditional:   339,480 tokens per correct implementation
Agent-native:  371,165 tokens per correct implementation
```

The cost per **correct implementation** is only **9.3% higher** for agent-native, yet agent-native achieves **45% more correct implementations** (16 vs 11 passing runs).

**Where traditional tokens are wasted**: Failed runs involve 4-11 reads followed by a wrong implementation. Those tokens generated zero value. Agent-native invests the same token budget in upfront research, avoiding valueless failed runs.

**Token timing arbitrage:**
- Traditional model: save tokens upfront, pay for failed implementations later
- Agent-native model: invest tokens in research upfront, guarantee a correct first attempt

The aggregate cost per correct answer is nearly identical. The agent-native repo simply front-loads the investment.

---

## Mechanism 5: Information Density Difference

The extra files agent-native reads are not ordinary source code — they are high-density metadata:

| Read Target | Information Returned Per Read |
|-------------|------------------------------|
| `userController.ts` | "Here's the CRUD implementation; infer where to add new functionality" |
| `MANIFEST.yaml#user.delete` | "Handler at X, side_effects: writes_user_store, known_issues: sessions not invalidated" |
| `INVARIANTS.md` | "INV-002: bug is in `user.delete.handler.ts`, fix by calling `deleteSessionsByUserId()`" |

**Same single Read call, but 5-10x more actionable information.**

This is why agent-native uses more reads but achieves higher token efficiency per correct answer — each read has higher expected value.

---

## Mechanism 6: Counter-Example Analysis (Tasks E and G)

Agent-native underperformed on Task E (password change, -50pp) and Task G (email search, -50pp). These failures reveal the opposing force.

**Task E data:**
```
trad run1: read=8,  edit=2  → PASS  (simple: find controller, add validation, done)
AN   run1: read=10, edit=4  → FAIL  (read contract + INVARIANTS on password security,
                                      then implemented extra validation layers)
```

Agent-native read `INVARIANTS.md` entry `INV-001: passwords must use bcrypt, saltRounds >= 10, never return password in response`. It incorporated this constraint into the implementation — adding extra validation that broke existing test boundary conditions.

**The Curse of Knowledge**: Too much information led to over-engineering. Simple tasks don't need full context; the context actively misguides.

**The task complexity spectrum:**

```
High hidden complexity  (H, J):  agent-native +100pp
Medium complexity       (A, B, I): agent-native +50pp
Low complexity          (D, F):  both equal, ~0pp
Low complexity + noisy .agent/  (E, G): agent-native -50pp
```

---

## Synthesis: Three Competing Forces

Agent-native repos exert three simultaneous forces on the agent:

```
Force 1 (positive): Front-loaded knowledge effect
  Read .agent/ files → understand full constraints → correct decision
  Strongest for: complex tasks with implicit cross-module side effects

Force 2 (positive): Structure conformity effect
  Observe semantic file names + domain organization → create new isolated files
  → don't break existing logic
  Strongest for: tasks requiring new feature additions

Force 3 (negative): Information overload effect
  Read too many constraints → over-engineer simple changes → break edge cases
  Strongest for: simple, well-scoped tasks with obvious implementation
```

The net result of +25pp occurs because **Forces 1 and 2 dominate on complex tasks (which are harder and contribute disproportionately to failures), while Force 3 only affects simple tasks (where both repos already perform well).**

---

## Practical Implications for `/init-agent-repo`

| Finding | Design Implication |
|---------|-------------------|
| Premature commit is the #1 failure cause | AGENT.md must open with: "Before editing ANY file, read .agent/INVARIANTS.md and MANIFEST.yaml" |
| IMPACT_MAP solves unknown unknowns | Every file needs "if you change this, you also need to change..." declarations |
| Structure is the silent instruction | File naming conventions should be enforced via lint rules, not just documentation |
| Simple tasks don't need complex metadata | Keep INVARIANTS.md focused on non-obvious constraints only — don't document what's evident from the code |
| Read-per-edit ratio is a quality signal | AGENT.md can hint: "Confirm you've read all relevant contract files before making any edits" |

---

## Why More Tokens ≠ Waste

The standard intuition is: fewer tokens = more efficient. This experiment shows the correct framing is: **tokens invested before the first edit are worth more than tokens spent debugging failed implementations**.

Consider Task H (auth refresh):
- Traditional: spends ~125K tokens → wrong implementation → tests fail → total value: 0
- Agent-native: spends ~466K tokens → correct implementation → tests pass → total value: 1

The traditional agent "saved" tokens and got nothing. The agent-native agent spent more and got everything. Efficiency is measured per correct outcome, not per run.

---

## One-Sentence Summary

> **Traditional agents fail not because they lack capability, but because they lack information — they begin modifying code before they understand the full constraint space. Agent-native repositories force upfront information acquisition, converting the cost of "tokens-for-information" from post-failure debugging into pre-commit research, thereby transforming retry cost into first-attempt success rate.**
