# 深度分析：为什么 Agent-Native 工具调用更多，正确率却更高？

> 基于 40 次真实实验运行的数据挖掘

---

## 核心悖论

实验数据呈现出一个反直觉的结果：

| | 传统仓库 | Agent-Native | 变化 |
|--|---------|-------------|------|
| 平均工具调用 | 9.0 | 14.0 | +55.6% |
| 平均 token 消耗 | 189,518 | 300,779 | +58.7% |
| 测试通过率 | 55% | **80%** | **+25pp** |

**更多资源投入 → 更好的结果。** 这不是"效率提升"，而是"投资回报的重新分配"。下面逐层拆解这个机制。

---

## 机制一：过早提交（Premature Commit）

**最关键的发现。**

观察传统仓库失败时的读取次数：

```
task-a  传统 run2: read=5  edit=2  → FAIL（只读了 5 个文件就提交了）
task-b  传统 run1: read=7  edit=2  → FAIL（只读了 7 个文件就提交了）
task-h  传统 run1: read=4  edit=2  → FAIL（只读了 4 个文件就提交了）
task-h  传统 run2: read=5  edit=2  → FAIL（只读了 5 个文件就提交了）
task-j  传统 run1: read=11 edit=6  → FAIL
task-j  传统 run2: read=7  edit=6  → FAIL
```

对比同任务的 Agent-Native 成功运行：

```
task-h  AN  run1: read=19 edit=5   → PASS（读了 19 个文件才提交）
task-h  AN  run2: read=14 edit=4   → PASS
task-j  AN  run1: read=19 edit=5   → PASS
task-j  AN  run2: read=13 edit=7   → PASS
```

**Pattern 极其清晰**：传统 agent 读了 4-7 个文件就认为"够了"，开始修改，结果修改了错误的地方或遗漏了关键文件。Agent-native agent 读了 13-19 个文件，但每次修改都是正确的。

**根本原因**：传统 repo 没有任何信号告诉 agent"你还没读完关键信息"。Agent-native repo 的 AGENT.md 第一行就说 "Read .agent/INVARIANTS.md before touching anything"，强迫 agent 先建立完整的上下文。

### 读写比（Read-per-Edit Ratio）

一个新的指标，可以量化这个现象：

```
task-j  传统 run1: ratio=1.8 r/e  → FAIL
task-j  传统 run2: ratio=1.2 r/e  → FAIL
task-j  AN  run1:  ratio=3.8 r/e  → PASS
task-j  AN  run2:  ratio=1.9 r/e  → PASS
```

Agent-native agent 在每次修改前读取了更多文件。它是"多调研、少动手"的工作模式，而传统 agent 是"读一点就开始改"。

---

## 机制二：缺失的文件修改（Missing Edit Problem）

传统 agent 和 agent-native agent 有时修改相同数量的文件——但传统 agent 改了错误的文件组合。

**Task J（软删除）成功运行的 Edit 分布：**

```
传统：  edit=6 → FAIL（改了 6 次，但改的是同一个 delete handler 的反复修改）
AN：    edit=5 → PASS（改了 5 个不同的文件：delete handler + get handler + session 清理 + ...）
```

软删除需要同时修改三处：
1. delete handler（添加 `deletedAt`）
2. get handler（对软删除用户返回 404）
3. session 注销（删除时清除 session）

传统 agent 只找到了 delete handler，反复修改它；agent-native 通过 IMPACT_MAP.yaml 知道"修改 user.delete.handler 会影响 user_store 和 session_store"，因此主动找到了其余两个文件。

**本质**：传统 agent 不知道自己不知道什么（unknown unknowns）。Agent-native 的 IMPACT_MAP 把 unknown unknowns 变成了 known unknowns。

---

## 机制三：文件创建模式（Write Ratio）

```
传统仓库：   Write=2   Edit=47   Write 占比 4.1%
Agent-Native: Write=12  Edit=57   Write 占比 17.4%
```

Agent-native agent 创建新文件的频率是传统 agent 的 **4 倍**。

**为什么重要？**

传统 repo 的 `src/controllers/userController.ts` 里混合了所有用户操作。当 agent 要添加新功能时，它的直觉是"找到最相关的已有文件，往里加代码"——结果是往一个大文件里堆加逻辑，引入副作用。

Agent-native repo 的结构是 `src/user/user.create.handler.ts`、`src/user/user.get.handler.ts`... 每个操作一个文件。当 agent 看到这个模式，它的直觉是"我应该创建 `user.update-email.handler.ts`"——结果是创建了一个独立的、职责单一的文件，不会破坏已有逻辑。

**结构即规范（Structure as Convention）**：仓库结构本身就是对 agent 的无声指令。

---

## 机制四：Token 的真实效率

表面上看，agent-native 用了更多 token。但换个角度：

```
传统仓库：  339,480 tokens / 每次正确答案
Agent-Native: 371,165 tokens / 每次正确答案
```

每次**正确实现**的 token 成本只贵了 **9.3%**，但 agent-native 获得了 **45% 更多的正确答案**（16 vs 11）。

**传统 token 的浪费**：失败的运行里，传统 agent 用了 4-11 次读取，然后写了一个错误的实现。这些 token 产生了零价值。Agent-native 把同样的 token 预算花在了前置调研上，避免了无效的失败运行。

**Token 的时间价值**：
- 传统模型：先省 token，后花时间在失败的修改上
- Agent-native 模型：先花 token 在调研上，保证修改一次成功

---

## 机制五：信息密度差异（Information Density）

Agent-native 额外读的文件不是普通源码，而是高密度元数据：

| 读取目标 | 每次读取获得的信息 |
|---------|----------------|
| `userController.ts` | "这里有 CRUD 实现，你需要推断哪里可以添加新功能" |
| `MANIFEST.yaml#user.delete` | "Handler 在这个文件，副作用是 writes_user_store，已知问题：不注销 session" |
| `INVARIANTS.md` | "INV-002：bug 在 `user.delete.handler.ts` 第 X 行，修复方法是调用 `deleteSessionsByUserId()`" |

**同样是一次 Read 调用，但信息量差了 5-10 倍。**

这就是为什么 agent-native 读取次数更多但 token 效率更高——每次读取回报更高。

---

## 机制六：反例分析（Tasks E、G 的失败）

Agent-native 在 Task E（密码修改）和 Task G（邮箱搜索）上反而更差，这揭示了另一个机制。

**Task E 数据：**
```
传统 run1: read=8, edit=2 → PASS（简单：找到 controller，加密码验证，完成）
AN   run1: read=10, edit=4 → FAIL（读了 contract、INVARIANTS 关于密码安全的条目，然后实现了额外的验证层）
```

Agent-native 读到了 `INVARIANTS.md` 里的 `INV-001: 密码必须 bcrypt，saltRounds >= 10，禁止在响应中返回密码`。它把这条约束纳入了实现，反而做了过多的验证，破坏了已有测试的边界条件。

**"知识的诅咒"（Curse of Knowledge）**：信息太丰富，导致实现过于复杂。简单任务不需要完整上下文，反而被上下文误导。

**规律**：Agent-native 的优势与任务的"隐性复杂度"成正比：

```
隐性复杂度高（H、J）：agent-native +100pp
隐性复杂度中（A、B、I）：agent-native +50pp
隐性复杂度低（D、F）：两者持平
隐性复杂度低但 .agent/ 有干扰信息（E、G）：agent-native -50pp
```

---

## 综合：三种力的竞争

Agent-native repo 对 agent 同时施加三种力：

```
力 1（正）：前置知识效应
  读 .agent/ 文件 → 知道完整约束 → 正确决策
  最强场景：含隐式依赖的复杂任务

力 2（正）：结构模仿效应
  看到语义化文件名 + 领域组织 → 创建新独立文件 → 不破坏已有逻辑
  最强场景：需要添加新功能

力 3（负）：信息过载效应
  读了过多约束 → 过度实现 → 破坏已有边界
  最强场景：目标明确的简单任务
```

最终结果 +25pp 是因为：**力 1 和力 2 在复杂任务上的正向影响，大于力 3 在简单任务上的负向影响**。

---

## 关键设计启示

| 发现 | 对 `/init-agent-repo` skill 的启示 |
|-----|----------------------------------|
| 前置调研不足是失败的首因 | AGENT.md 开头必须强制写："在动任何文件前，先读 .agent/INVARIANTS.md 和 MANIFEST.yaml" |
| IMPACT_MAP 解决 unknown unknowns | 每个文件都要有"如果你改这里，还需要改哪里"的声明 |
| 结构本身就是规范 | 文件命名约定应通过 lint rule 强制，而非只靠约定 |
| 简单任务不需要复杂元数据 | MANIFEST 应该简洁，不要把所有 invariants 堆在一个文件——只标注 non-obvious 的约束 |
| 修改前读取比（r/e ratio）是质量指标 | AGENT.md 可以提示："确认你已读取所有相关 contract 文件再开始修改" |

---

## 一句话总结

> **传统 agent 失败的根本原因不是"能力不够"，而是"信息不够"——它在信息不完整的情况下就开始修改代码。Agent-native 仓库通过强制前置信息读取，把"用 token 换信息"的时机从失败后的调试移到了修改前的调研，从而把试错成本转化为首次正确率。**
