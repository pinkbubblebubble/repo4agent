<div align="right">

<a href="README_CN.md">中文</a> | English

</div>

<div align="center">

<img src="docs/icon.svg" width="96" height="96" alt="Repo4Agent Icon" />

# Repo4Agent

### *The repository, redesigned for the agent that works in it.*

<p align="center">
  <a href="https://pinkbubblebubble.github.io/Repo4Agent/">
    <img src="https://img.shields.io/badge/Live%20Demo-Visit-6366f1?style=for-the-badge&logoColor=white" alt="Live Demo" />
  </a>
  <a href="reports/report_en.md">
    <img src="https://img.shields.io/badge/Experiment%20Report-Read-22d3ee?style=for-the-badge" alt="Report" />
  </a>
  <a href="skill/init-agent-repo/SKILL.md">
    <img src="https://img.shields.io/badge/Claude%20Skill-Install-4ade80?style=for-the-badge" alt="Skill" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Experiment%20Runs-40-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Tasks-10-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Pass%20Rate%20%2B25pp-55%25%20%E2%86%92%2080%25-brightgreen?style=flat-square" />
  <img src="https://img.shields.io/badge/Model-claude--haiku--4--5-lightgrey?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" />
</p>

</div>

---

## The Problem

AI agents working in a codebase read the wrong files, miss cross-module side effects, and commit changes before they understand the full constraint space. They weren't designed for it — the codebase was designed for humans.

**Repo4Agent** is a controlled empirical study: what happens when you redesign a repository for the agent that will work in it, not the human who wrote it?

We ran **40 controlled experiment runs** across 10 tasks and 2 repo types using `claude-haiku-4-5-20251001`. The results:

<div align="center">

| Metric | Traditional | Agent-Native | Delta |
|:--|:-----------:|:------------:|:-----:|
| Avg tool calls | 9.0 | 14.0 | +55.6% |
| Avg tokens consumed | 189,518 | 300,779 | +58.7% |
| **Test pass rate** | **55%** | **80%** | **+25pp** |
| Cost per correct impl. | 339K tok | 371K tok | +9.3% |

</div>

On the hardest tasks (hidden constraints, cross-module side effects): **0% → 100%**.

The agent-native approach uses *more* tokens and tool calls — yet produces *far* more correct answers. The extra reading cost pays for itself in implementation accuracy.

---

## Why It Works

### 1. Premature commit is the primary failure mode

Traditional agents read 4–7 files, conclude "that's enough context," and begin editing — typically the wrong files. Agent-native repos open with a **mandatory pre-read instruction** in `AGENT.md`, forcing agents to read 13–19 files before modifying anything. This alone is the single highest-impact structural change.

### 2. Side effects are the #1 unknown unknown

`MANIFEST.yaml` declares every operation's writes, reads, and downstream effects. Without it, an agent fixing a delete handler won't know it also needs to invalidate sessions. With it, the agent knows — because the manifest says so explicitly.

### 3. Structure is a silent instruction

Domain-organized source (`src/user/`, `src/auth/`) with semantic file names (`user.delete.handler.ts`) cues the agent to create new isolated files rather than pile into an existing controller. Agent-native runs show **4× more new file creation** and proportionally fewer unintended side effects.

> **The core insight:** Agent-native repos aren't code bases — they're APIs. They have schemas, contracts, and explicit side-effect declarations. Agents don't need to *understand* code; they need to locate the correct modification point in the fewest tool calls possible, and know the blast radius of any change.

---

## What Is an Agent-Native Repository?

An agent-native repo adds a **structured metadata layer** without changing a line of source logic. The API stays the same. The structure changes.

```
.agent/
  MANIFEST.yaml      ←  Every capability: handler path, side_effects, known_issues, test coverage
  INVARIANTS.md      ←  Non-obvious constraints, pre-annotated bugs with exact fix locations
  IMPACT_MAP.yaml    ←  "Changing X requires also changing Y" — converts unknowns to knowns
AGENT.md             ←  Machine-optimized entry: mandatory pre-read, capability index, stack
src/
  user/
    user.create.handler.ts    ←  One file per operation
    user.contract.ts
    user.test.ts
  auth/
    auth.login.handler.ts
    ...
```

### Impact Ranking (from experiment data)

| Feature | Measured Impact |
|:--------|:---------------:|
| `INVARIANTS.md` — pre-annotated bugs with WHERE + FIX | **Highest** |
| `MANIFEST.yaml` — `side_effects` + `known_issues` per operation | **High** |
| `IMPACT_MAP.yaml` — cross-module impact chains | **High** |
| Domain-organized source structure | **Medium** |
| Semantic file naming (`user.delete.handler.ts`) | **Medium** |
| `TASK_TEMPLATES/` per task type | **Low** |

---

## Results by Task

<div align="center">

| Task | Traditional | Agent-Native | Δ |
|:-----|:-----------:|:------------:|:-:|
| A: Add PATCH /email endpoint | 50% | 100% | +50pp |
| B: Fix sessions not invalidated on delete | 50% | 100% | +50pp |
| C: Input validation middleware | 0% | 0% | — |
| D: GET /users list endpoint | 100% | 100% | — |
| E: PATCH /password endpoint | 100% | 50% | **−50pp** |
| F: Session expiry fix | 100% | 100% | — |
| G: GET /users?email search | 100% | 50% | **−50pp** |
| **H: POST /auth/refresh** | **0%** | **100%** | **+100pp** |
| I: Global request logging | 50% | 100% | +50pp |
| **J: Soft delete + session invalidation** | **0%** | **100%** | **+100pp** |

</div>

**Tasks E and G are intentional counter-examples.** On simple, well-scoped tasks, agent-native underperforms — agents over-read the metadata and over-engineer the solution. The key design rule: keep `INVARIANTS.md` sparse. Document only non-obvious constraints.

**Agent-native advantage scales directly with hidden task complexity.**

---

## Quick Start: `/init-agent-repo` Skill

The experiment produced a Claude Code skill that generates the full agent-native metadata layer for any existing codebase automatically.

**Install**

```bash
mkdir -p ~/.claude/skills/init-agent-repo
cp skill/init-agent-repo/SKILL.md ~/.claude/skills/init-agent-repo/SKILL.md
```

Restart Claude Code, then run `/init-agent-repo` in any project.

**What it generates**

| File | Purpose |
|:-----|:--------|
| `AGENT.md` | Machine-optimized entry point with capability table and mandatory pre-read instruction |
| `.agent/MANIFEST.yaml` | Side effects, dependencies, and test coverage declared per operation |
| `.agent/INVARIANTS.md` | Active constraint violations with exact file locations and fix guidance |
| `.agent/IMPACT_MAP.yaml` | Cross-module impact chains linking every source file to what it breaks |

---

## Reproducing the Experiment

<details>
<summary><strong>Prerequisites & Setup</strong></summary>

- [Claude Code](https://claude.ai/code) installed and authenticated
- Python 3.8+, Node.js 18+

```bash
cd traditional-repo && npm install && cd ..
cd agent-native-repo && npm install && cd ..
```

</details>

<details>
<summary><strong>Run the experiment</strong></summary>

```bash
cd experiment

# 10 tasks × 2 repo types × 2 runs = 40 total
python3 run_experiment.py

# Aggregate results
python3 summarize.py
```

The runner uses `--disallowedTools Bash` to force the agent through discrete Read/Glob/Grep/Write/Edit calls — making tool-call counts reproducible and meaningful.

Results append to `experiment/results/raw_results.jsonl`:

```
repo_type, task_id, run_number,
read, glob, grep, write, edit,
input_tokens, output_tokens, total_tokens, cost_usd,
tests_passed, failed_test_count, duration_ms
```

</details>

---

## Repository Structure

```
repo4agent/
├── traditional-repo/          Standard Express.js + TypeScript (mixed controllers)
├── agent-native-repo/         Same API, restructured for agents
│   ├── .agent/                MANIFEST.yaml · INVARIANTS.md · IMPACT_MAP.yaml
│   ├── AGENT.md
│   └── src/user/ · src/auth/  Domain-organized, one file per operation
├── experiment/
│   ├── run_experiment.py      Experiment runner (claude CLI subprocess)
│   ├── parse_stream.py        stream-json parser, counts tool calls
│   ├── summarize.py           Aggregates → summary.json
│   └── results/               40 raw runs + aggregated data
├── reports/
│   ├── report_en.md           Full experiment report (methodology, per-task breakdown)
│   ├── analysis_en.md         Deep analysis: 6 mechanisms
│   └── *_cn.md                Chinese versions
├── skill/
│   └── init-agent-repo/SKILL.md
└── docs/index.html            Interactive demo (GitHub Pages)
```

---

## Further Reading

| Document | Language | Content |
|:---------|:--------:|:--------|
| [Experiment Report](reports/report_en.md) | EN | Methodology, per-task breakdown, hypothesis evaluation |
| [Deep Analysis](reports/analysis_en.md) | EN | 6 mechanisms: premature commit, missing edit, write ratio, token timing, information density |
| [实验报告](reports/report_cn.md) | 中文 | 方法论、任务分解、假设验证 |
| [深度分析](reports/analysis_cn.md) | 中文 | 6种机制分析 |

---

## Citation

```
Repo4Agent: Agent-Native Repository Design
40-run empirical comparison, claude-haiku-4-5-20251001, 2026
https://github.com/pinkbubblebubble/Repo4Agent
```

---

<div align="center">

<img src="docs/icon.svg" width="40" height="40" alt="" />

**Repo4Agent** — *Design your codebase for the agent that will work in it.*

<sub>40 experiment runs · 10 tasks · claude-haiku-4-5-20251001</sub>

</div>
