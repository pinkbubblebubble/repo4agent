# 深度分析：为什么 Agent-Native 工具调用更多，正确率却更高？

> 基于 80 次实验运行、4 个条件、10 个任务的机制性研究

---

## 核心悖论（更新版）

四条件实验产生了与最初两条件研究相同的反直觉发现——而消融实验使这一发现更加清晰：

| 条件 | 平均工具调用 | 平均 Token | 通过率 |
|------|------------|-----------|-------|
| Traditional | 9.0 | 189,518 | 55% |
| AN-Baseline | 14.0 | 300,779 | 80% |
| AN-Extended | 18.0 | 343,444 | 80% |
| AN-Refined | 13.5 | 293,141 | **85%** |

最重要的对比是 AN-Extended 与 AN-Refined 之间。AN-Extended 比 AN-Refined 多消耗 33% 的工具调用和 17% 的 Token——却取得了相同甚至更低的通过率。这是数据集中最有力的证据，证明**更多的元数据不等于更好的元数据**。

AN-Refined 同样以更少的资源超越了 AN-Baseline：85% vs. 80% 的通过率，平均 293K vs. 301K Token。此处的悖论是二阶的：不仅更多的探索提升了结果（相比 Traditional），更有针对性的指导比更全面的指导取得了更好的结果，同时成本也更低。

**每次正确实现的 Token 成本：**

```
Traditional：189,518 × 20 次运行 / 11 次正确 = 344,578 token/次正确
AN-Baseline：300,779 × 20 次运行 / 16 次正确 = 375,974 token/次正确
AN-Extended：343,444 × 20 次运行 / 16 次正确 = 429,305 token/次正确
AN-Refined：293,141 × 20 次运行 / 17 次正确 = 344,872 token/次正确
```

AN-Refined 和 Traditional 每次正确实现的成本几乎相同。区别在于：AN-Refined 用这个成本获得了 17 次正确答案；Traditional 只获得了 11 次。

---

## 机制一：过早提交（Premature Commit）

**所有条件中最主要的失败模式。**

传统 Agent 读取 4–7 个文件后就认为"上下文足够了，可以开始修改"。Agent-Native Agent 在动手之前会读取 13–19 个文件。Agent-Native 条件下额外的读取不是冗余的——正是这些读取揭示了使实现正确所必需的约束。

失败的 Traditional 运行的证据：

```
task-h  Traditional run1：read=4, edit=2  → FAIL（完全遗漏了 session 失效要求）
task-h  Traditional run2：read=5, edit=2  → FAIL（同样的遗漏）
task-j  Traditional run1：read=11, edit=6 → FAIL（6 次修改全在 delete handler；遗漏了 get handler + session）
task-j  Traditional run2：read=7,  edit=6 → FAIL（同样的模式）
```

同一任务 AN-Refined 成功运行的对比：

```
task-h  AN-Refined run1：total=40, explore=33 → PASS
task-h  AN-Refined run2：total=16, explore=11 → PASS
task-j  AN-Refined run1：total=49, explore=42 → PASS
task-j  AN-Refined run2：total=35, explore=30 → PASS
```

**过早提交的根本原因：** 传统仓库没有任何信号告诉 Agent"你还没有读取包含关键约束的文件"。Agent 的探索停止标准是内部的——仅基于源码的充分感。Agent-Native 仓库将约束空间外部化：AGENT.md 明确指示"在修改任何文件之前先读取 INVARIANTS.md 和 MANIFEST.yaml"，将 Agent 的停止标准重置为"我已经读完了声明的约束文件"。

### 读写比（Read-per-Edit Ratio）作为质量信号

量化提交前探索深度的衍生指标：

```
task-j  Traditional run1：reads=11, edits=6  → ratio=1.8  → FAIL
task-j  Traditional run2：reads=7,  edits=6  → ratio=1.2  → FAIL
task-j  AN-Refined  run1：reads=42, edits=7  → ratio=6.0  → PASS
task-j  AN-Refined  run2：reads=30, edits=5  → ratio=6.0  → PASS
```

在复杂任务上，读写比低于约 2.0 强烈预示失败；高于约 4.0 则预示成功。Agent-Native 仓库通过声明某些文件必须在编辑开始前读取，从结构上提升了这一比率。

**AN-Refined 与 AN-Baseline 在过早提交上的对比：** AN-Refined 比 AN-Baseline 更高效地解决了过早提交问题。Task H 上，AN-Baseline 平均探索 21.0 次；AN-Refined 平均 11.5 次——而两者均实现 100% 通过率。TEST_CONTRACTS.yaml 为 Agent 提供了更清晰的目标，使其用更少的探索读取就能达到实现信心。

---

## 机制二：缺失的文件修改——将未知变为已知

传统 Agent 有时与 Agent-Native Agent 进行了相同数量的文件修改，但修改的是错误的文件组合。这就是"缺失文件修改"问题：由于仓库没有提供跨模块依赖信号，Agent 并不知道自己遗漏了某个文件。

**Task J 传统失败运行的 Edit 分布：**

```
Traditional run1：edit=6 → FAIL（全部 6 次修改都在 user.delete.handler.ts 上）
Traditional run2：edit=6 → FAIL（同样的模式）
```

**Task J AN-Refined 成功运行的 Edit 分布：**

```
AN-Refined run1：修改分散在 delete handler、get handler、db.ts、session 清理
AN-Refined run2：同样的分散模式
```

软删除需要三处协调修改：delete handler（添加 `deletedAt`）、get handler（对软删除用户返回 404）、session 清理。传统 Agent 找到了 delete handler 并将其实现消耗殆尽。`IMPACT_MAP.yaml` 声明了：

```yaml
src/user/user.delete.handler.ts:
  affects:
    - target: "src/user/user.get.handler.ts"
    - target: "_shared/db.ts"
    - target: "src/auth/auth.session.handler.ts"
```

这将问题从未知未知（"我不知道这个改动有哪些副作用"）转化为已知未知（"IMPACT_MAP 告诉我需要检查这三个文件"）。Agent 读取全部三个文件，并发现了所需的修改。

**IMPACT_MAP 为何具有独特价值：** 源码可以告诉 Agent 逻辑在哪里。它无法告诉 Agent 当该逻辑改变时，哪些其他逻辑会出问题。IMPACT_MAP 将有经验的开发者脑中隐式的耦合关系外部化。

---

## 机制三：结构即无声指令

Agent-Native 仓库不仅文档更好——它们在结构上也不同。文件命名和组织模式本身就是对如何添加新代码的隐式指令。

**各条件的 Write 比率：**

```
Traditional：  Write≈2   Edit≈47  Write 比率 ≈ 4%
AN-Baseline：  Write≈12  Edit≈57  Write 比率 ≈ 17%
AN-Refined：   与 AN-Baseline 相近
```

Agent-Native Agent 创建新文件的频率约是传统 Agent 的 4 倍。

**为何重要：** 传统 `src/controllers/userController.ts` 混合了所有用户操作。Agent 的直觉："找到最相关的现有文件，往里添加代码。"结果：一个臃肿的文件，新代码的副作用与现有逻辑纠缠在一起。

Agent-Native 的 `src/user/user.create.handler.ts`、`src/user/user.get.handler.ts`——每个操作一个文件。Agent 的直觉："我应该创建 `src/user/user.update-email.handler.ts`。"结果：一个单一职责的文件，除了明确的导入外不与现有代码交互。

这就是**结构模仿效应**：仓库布局本身传达了预期的代码组织方式。阅读代码库的新开发者会做出同样的推断。区别在于，这种推断对 AI Agent 的可靠性远高于散文文档——因为文件系统结构是明确无误的，而文档是可解读的。

Write 比率的提升同样减少了功能添加任务上的主要失败模式：传统 Agent 的单文件编辑会引入与现有逻辑的意外交互；AN Agent 的新文件创建从构造上就是隔离的。

---

## 机制四：Token 时间价值套利

表面视角：Agent-Native 使用了更多 Token。正确视角：Agent-Native 将 Token 投资前置，以避免毫无价值的失败运行。

**失败运行中传统 Token 的分配：**
- 阶段一（探索）：4–7 次 Read 调用 → ~40K Token
- 阶段二（实现）：2 次 Edit 调用 → ~10K Token
- 合计：~50K Token → 错误实现 → 测试失败 → **零价值产出**

**AN-Refined 成功运行中的 Token 分配：**
- 阶段一（元数据读取）：AGENT.md + INVARIANTS.md + MANIFEST.yaml + TEST_CONTRACTS.yaml → ~30K Token，高信息密度
- 阶段二（源码探索）：8–12 次有目的的 Read 调用 → ~80K Token
- 阶段三（实现）：2–4 次有正确目标的 Edit 调用 → ~15K Token
- 合计：~125K Token → 正确实现 → **全价值产出**

传统 Agent "节省"了约 75K Token 的探索，却将其花在了毫无价值的实现上。AN-Refined Agent 多投入了约 75K Token 用于探索，从根本上消除了产出无价值实现的可能性。

**不对称性：** 失败的实现运行不仅仅是"零价值"——在真实的 CI/CD 环境中，它还意味着反馈延迟、开发者审查时间和重试成本。Agent-Native 模式对于关键任务完全消除了这些下游成本。

**横跨所有 80 次运行：**
```
AN-Refined 每次正确实现的成本：
  293,141 token × 20 次运行 / 17 次正确 ≈ 344,900 token/次正确

Traditional 每次正确实现的成本：
  189,518 token × 20 次运行 / 11 次正确 ≈ 344,600 token/次正确
```

每次正确答案的成本几乎相同。AN-Refined 只是在同样的成本下产生了更多正确答案。

---

## 机制五：信息密度——每次读取为何返回更多信息

Agent-Native Agent 额外读取的文件不是普通的源码，而是专门为高密度摘要非可推断信息而构建的文件。

| 读取目标 | 信息类别 | 所需 Token | 可操作信息 |
|---------|---------|-----------|----------|
| `userController.ts`（300 行） | 实现 | ~3,000 token | "这里是 CRUD 逻辑；推断在哪里添加新功能" |
| `MANIFEST.yaml#user.delete` | 能力声明 | ~200 token | "Handler 在此文件，side_effects: [Y, Z]，known_issues: [W]" |
| `INVARIANTS.md`（INV-002） | Bug 声明 | ~150 token | "Bug 在此处；步骤一：做这件事；步骤二：做那件事" |
| `TEST_CONTRACTS.yaml#task_E` | 测试断言声明 | ~100 token | "测试检查这些字段；不检查这些其他字段" |

元数据文件的信息/Token 比率约是源码文件的 5–10 倍，对于决定实现是否正确的特定信息类别（约束知识、副作用知识、测试边界知识）而言尤其如此。

这就是为什么 Agent-Native Agent 读取次数更多，但每次正确答案的 Token 效率更高——元数据读取的预期价值远高于额外的源码读取。

**为何源码读取无法替代：** 源码告诉你当前实现做了什么。它无法告诉你哪些约束必须在整个系统中保持不变，测试套件具体检查什么，或者哪些方法在被调用前需要先被创建。这些都需要外部声明。

---

## 机制六：TEST_CONTRACTS——防止过度工程化

这一机制是消融实验的新发现，专属于 AN-Refined。

**过度工程化失败模式：** AN-Baseline Agent 在读取与安全相关的 INVARIANTS.md 条目后，将这些约束纳入了超出测试要求范围的实现。结果是实现在技术上更为正确（更好的 bcrypt 处理、更全面的验证），但由于意外的副作用导致实际测试失败。

核心问题：INVARIANTS.md 告诉 Agent 系统*应该*做什么。TEST_CONTRACTS.yaml 告诉 Agent 测试*实际上*验证什么。这两者并不相同，在测试覆盖不完整的代码库中尤其如此。没有 TEST_CONTRACTS 时，Agent 按约束实现；有了 TEST_CONTRACTS，Agent 按测试实现。

**Task E 案例分析：**

AN-Baseline 失败模式：
```
Agent 读取 INV-001："密码必须使用 bcrypt，saltRounds >= 10"
Agent 实现：密码修改 + bcrypt 重新哈希 + 额外验证层
测试失败：额外验证层拒绝了测试期望通过的输入
```

AN-Refined 成功模式：
```
Agent 读取 TEST_CONTRACTS："测试仅检查状态码；不测试 bcrypt 内部实现"
Agent 实现：密码修改 + 当前密码验证（仅此）
测试通过：实现与测试验证的内容精确匹配
```

**Task G 案例分析（类似模式）：** AN-Baseline Agent 根据 MANIFEST 对用户查询 API 的描述推断出了额外的过滤逻辑，并以与现有路由处理程序结构冲突的方式实现了邮箱搜索。TEST_CONTRACTS.yaml 精确说明了"返回用户数组；不测试分页或额外过滤器"，两次 AN-Refined 运行均通过。

**一般原则：** 当 Agent 在编写代码前就知道精确的测试范围，它就不会添加超出该范围的代码。TEST_CONTRACTS.yaml 本质上是一个作用域说明——它以可验证断言的形式告诉 Agent 每个任务"完成"意味着什么。

---

## 机制七：修复说明的顺序——先创建再调用

这一机制同样是消融实验的新发现，解释了 AN-Extended 在 Task B 上的退步以及 AN-Refined 的恢复。

**失败原因：** AN-Extended 的 INVARIANTS.md 对 INV-002 的描述：

```
INV-002：session-用户一致性
  修复：删除用户后调用 sessionStore.deleteByUserId(userId)
```

Agent 调用了 `sessionStore.deleteByUserId(userId)`。这个方法在代码库中不存在。AN-Extended Task B 的两次运行中有一次失败，原因是 Agent 在没有检查方法是否存在的情况下就直接调用了它。

**原因分析：** 修复说明是面向动作的，却不是面向创建的。"调用 X"隐式假设 X 已经存在。当 X 不存在时，Agent 仍然调用它——因为它正在正确地遵循指令。

**AN-Refined 的修复说明：**

```markdown
INV-002：Session-用户一致性（已违反）
  步骤一：在 _shared/db.ts 中添加 `deleteByUserId(userId: string)`。
          此方法当前不存在。参考 deleteSessionsForEmail 的实现模式。
  步骤二：在 user.delete.handler.ts 中，删除用户后调用 db.deleteByUserId(userId)。
```

逐步结构迫使 Agent 在调用方法之前先创建它。AN-Refined 的 Task B 两次运行均通过。

**可推广的原则：** INVARIANTS.md 中的修复说明必须反映修复的实际依赖顺序，包括创建尚不存在的方法或接口。"调用 X"只有在 X 存在时才是完整的指令。当 X 不存在时，完整的指令是"创建 X（这里说明在哪里以及如何创建），然后调用 X"。

这类似于代码注释"// TODO: 重构这里"与逐步代码审查意见"步骤一：将这段代码提取到名为 `processSession` 的函数中。步骤二：在登录和刷新两个处理程序中调用 `processSession`"之间的区别。后者是可按序执行的；前者不是。

---

## 反例及其揭示的问题

实验产生了三类反例，限定了 agent-native 假设的适用边界。

### 反例集一：Task C（全条件 0%）

输入验证在所有四个条件下均失败。失败不是元数据问题——而是测试覆盖问题。测试套件不包含任何输入验证行为的断言。Agent 正确实现了验证功能，但其实现中的边界情况处理导致原有测试失败。

**揭示的问题：** Agent-Native 元数据可以揭示已知约束和已知测试边界。它无法为不存在的测试覆盖创造替代品。Task C 需要 TEST_CONTRACTS.yaml 说明"此能力没有测试；请谨慎实现"——但这只影响 Agent 的实现策略，无法解决根本上缺乏可验证正确性标准的问题。

### 反例集二：AN-Refined 在 Task I 上的退步（50%）

请求日志在 AN-Baseline 和 AN-Extended 中均通过 100%，但在 AN-Refined 中降至 50%。严格的日志格式 `[timestamp] METHOD /path -> STATUS (Xms)` 被测试验证；AN-Refined 的一次运行产生了不同的格式。

**揭示的问题：** Task I 的退步是在 AN-Refined 中移除 PATTERNS.yaml 和 CONCEPTS.yaml 的直接后果。这些文件显然描述了包括输出格式在内的实现约定。在没有确保 TEST_CONTRACTS.yaml 覆盖格式约束的情况下就移除这些文件，导致了退步。

这是实验中最直接的证据，表明最优元数据集需要系统性的覆盖分析——移除任何文件之前，必须验证其包含的信息要么（a）可以从源码推断，要么（b）已经迁移到其他地方。AN-Refined 的 TEST_CONTRACTS.yaml 中 Task I 的条目没有说明精确的日志格式，本应如此。

### 反例集三：AN-Baseline 在 E 和 G 上的失败（过度工程化）

已在机制六中详细分析。这些是推动增加 TEST_CONTRACTS.yaml 的案例。它们揭示：当任务不需要实现安全属性时，涵盖安全属性的 INVARIANTS.md 条目可能是有害的——Agent 过度阅读并过度工程化。

---

## 综合：最优元数据集假设

消融数据支持一个关于 agent-native 元数据应该包含什么内容的具体假设：

> **最优元数据集由以下信息的最小集合组成：Agent 无法合理地从源码推断、且决定其实现是否正确的信息。**

三类无法推断、决定正确性的信息：

1. **跨模块副作用** — 修改文件 X 时哪些东西会出问题。源码展示 X 做什么；它不展示什么依赖于 X 的行为保持稳定。（IMPACT_MAP.yaml、MANIFEST.yaml `side_effects`）

2. **已知 Bug 及逐步修复说明** — Agent 无法通过读取测试发现的 Bug 的位置、原因和有序修复步骤。步骤顺序必须与依赖顺序一致（先创建，再调用）。（INVARIANTS.md）

3. **测试断言边界** — 测试实际上检查什么，以及明确不检查什么。这将实现空间精确限定在所需范围内。（TEST_CONTRACTS.yaml）

其他所有内容——路由清单、文件列表、概念定义、提交规范、变更历史——要么可以从源码推断，要么只是增加噪音而不增加与决策相关的信息。

**元数据量反模式：** AN-Extended 证明了添加全面元数据在更高的 Token 投入下反而降低了性能。机制：当 Agent 拥有超出需要的元数据时，它（a）花更多时间阅读，（b）尝试将所有内容综合到实现中，（c）产生相对于测试范围过度规格化的实现。只有当所有元数据都属于上述三类无法推断、决定正确性的信息时，更多元数据才是更好的。

---

## 对 `/init-agent-repo` 的实践启示

| 机制 | 设计启示 |
|------|---------|
| 过早提交 | AGENT.md 必须明确规定：在进行任何编辑之前，先读取 INVARIANTS.md、MANIFEST.yaml、TEST_CONTRACTS.yaml |
| 未知未知 | 为所有具有非显而易见跨模块副作用的文件提供 IMPACT_MAP.yaml |
| 修复说明顺序 | INVARIANTS.md 必须使用逐步格式；步骤必须按依赖顺序排列 |
| 过度工程化 | 为每个任务提供 TEST_CONTRACTS.yaml；包含 `does_not_test` 条目 |
| 信息密度 | 元数据文件应声明事实；源码应实现逻辑——不要重复 |
| Task I 式退步风险 | 移除任何元数据文件之前，审查其包含的信息是否已被 TEST_CONTRACTS.yaml 覆盖 |

---

## 一句话总结（更新版）

> **传统 Agent 失败的根本原因不是"能力不足"，而是缺乏有针对性的、无法推断的信息——具体而言，是跨模块副作用、有序的逐步修复说明以及测试断言边界；而只提供这三类信息（不多也不少）的 Agent-Native 仓库，能够将前置调研的成本转化为首次正确率，同时实现与传统方式几乎相同的每次正确实现 Token 成本。**
