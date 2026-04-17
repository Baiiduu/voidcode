# 后台任务结果读取与 leader 通知契约

来源 issue：#139

## 目的

定义一层缺失的、由 runtime 拥有的契约，使后台任务的完成结果能够被 leader session 可靠感知和消费。

当前 runtime 已经具备 background task substrate，但仍缺少以下稳定契约：

- leader 可见的后台任务生命周期通知
- 结构化结果读取面
- 后台子任务 transcript 的恢复路径
- 通知的去重与重启恢复语义

## 状态

**状态：proposed**

本文档是面向后续实现的设计/契约文档，**不**表示当前 runtime 已经拥有这些能力。

## 问题陈述

今天的 VoidCode 已经可以：

- 启动、加载、列出和取消后台任务
- 在 workspace-local SQLite 中持久化后台任务真相
- 让后台任务继续走现有 runtime 执行路径

但它仍然不能可靠支持如下 async delegation 语义：

1. leader 启动一个后台任务
2. leader 继续执行或稍后恢复
3. 后台任务完成、失败、取消，或进入 approval-blocked 状态
4. leader 被 runtime 可靠通知
5. leader 读取结构化结果摘要，或恢复完整的子任务 transcript

如果没有这层契约，未来的 async agent flow 仍会退化成 prompt hack、轮询拼接或 client-local 推断，而不是 runtime truth。

## 目标

issue #139 需要定义一层最小但可靠的 runtime-owned 契约，覆盖：

1. **后台结果读取**
2. **leader 通知**
3. **足够支撑恢复的 parent/child linkage**
4. **顺序与去重语义**
5. **让 hooks / clients 消费 runtime truth，而不是自行发明语义**

## 非目标

本 issue **不**扩展到：

- scheduler 或 scheduled runs 设计
- 完整 multi-agent orchestration 语义
- 由 prompt 文本承载的伪通知模型
- 仅由客户端 toast/banner 构成的通知模型
- 替代现有 session replay / resume 契约
- 在 session persistence 之外再发明第二套 execution truth

## 当前基线

runtime 已有的基础能力：

- `BackgroundTaskState`，包含 `queued/running/completed/failed/cancelled` 状态
- `start_background_task` / `load_background_task` / `list_background_tasks` / `cancel_background_task`
- workspace-local 的后台任务持久化
- 已有的 session truth，以及通过 `resume(session_id)` 恢复 transcript 的路径

runtime 仍缺少：

- 面向 leader 的 parent session linkage
- 稳定的后台结果读取契约
- 注入到 leader session 的 runtime-owned notification flow
- 稳定进入客户端事件契约的 background-task 事件词汇表

## 所有权边界

这层能力必须继续由 **runtime** 拥有。

这意味着：

- 生命周期真相属于 `runtime/`
- 通知投递语义属于 `runtime/`
- 结果读取语义属于 runtime contracts 与持久化状态
- hooks 与 clients 只能消费这层真相，而不能定义它

它**不能**由以下位置拥有：

- hook 脚本
- prompt 约定
- Web/TUI 的本地状态
- 未来的 scheduler 子系统

## 必需的 runtime truth

### 1. Parent / Child Linkage

凡是需要通知 leader 的 delegated/background task，都必须显式携带 leader session linkage。

最小要求：

- `parent_session_id: str | None`

解释：

- `None` 表示这是普通后台任务，没有 leader-notification target
- 非空值表示 runtime 必须把该 session 当作通知目标

当前实现中的 `BackgroundTaskState.session_id` 已经表示后台运行生成的结果 session。为了避免与现有 `session_id` 泛称冲突，本文档统一使用：

- `task_id`：后台任务 id
- `parent_session_id`：leader session id
- `child_session_id`：后台子任务对应的结果 session id

并明确约定：

- **在当前代码语境中，`child_session_id` 对应 `BackgroundTaskState.session_id`**

## 结果读取契约

issue #139 应提供独立的结果读取面，而不是要求调用方自己拼接多个低层 API。

### 建议形状

```python
@dataclass(frozen=True, slots=True)
class BackgroundTaskResult:
    task_id: str
    parent_session_id: str | None
    child_session_id: str | None
    status: Literal[
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
    approval_blocked: bool
    summary_output: str | None
    error: str | None
    result_available: bool
```

### 建议 runtime operation

```python
def load_background_task_result(task_id: str) -> BackgroundTaskResult: ...
```

### 语义说明

- `load_background_task(task_id)` 继续作为低层 task-status surface
- `load_background_task_result(task_id)` 作为 leader-facing retrieval surface
- `summary_output` 是面向 leader 的紧凑结果摘要，仅在可安全暴露时出现
- `child_session_id` 指向完整 child transcript；完整 transcript 继续通过已有的 `resume(child_session_id)` 路径读取
- `result_available` 只在 runtime 能安全暴露摘要结果或 child transcript pointer 时为 `true`
- `approval_blocked` 是**结果视图上的派生字段**，不是对 `BackgroundTaskState.status` 的扩展
- 当 child session 的 `SessionState.status == "waiting"` 时，`approval_blocked` 应为 `true`

## Transcript 恢复契约

完整 delegated/background history **不应**复制进 leader session。

正确模型应是：

- leader 收到一条 runtime-owned notification event，其中始终包含 `task_id`，并在 child session 已建立时包含 `child_session_id`
- 完整 child transcript 继续保持为 session-scoped truth
- 当 `child_session_id` 存在时，调用方通过现有 `resume(child_session_id)` 路径恢复 child transcript

这保持了当前 runtime 模型的一致性：

- parent session 拥有 leader 可见通知
- child session 拥有 delegated execution history

## 通知契约

leader notification 必须表现为**附加到 parent session 上的 runtime events**。

### 需要稳定化的事件

- `runtime.background_task_completed`
- `runtime.background_task_failed`
- `runtime.background_task_cancelled`
- `runtime.background_task_waiting_approval`

这四类事件已经足够覆盖 issue #139 的最小 leader-notification 需求。

本文档**不**要求在 #139 中额外引入 `runtime.delegated_result_available` 作为独立事件；对于最小实现，生命周期事件本身已经可以承载 `result_available` 与 `summary_output` 等字段。

### parent-session payload 基线

所有 leader-notification events 至少应包含：

```json
{
  "task_id": "task-123",
  "parent_session_id": "session-leader",
  "status": "completed",
  "result_available": true
}
```

如果某个事件对应的 child session 已经建立，则该 payload 可以额外包含：

```json
{
  "child_session_id": "session-worker"
}
```

### 各事件 payload

#### `runtime.background_task_completed`

- `task_id`
- `parent_session_id`
- `child_session_id`
- `status: "completed"`
- `summary_output`（可选）
- `result_available: true`

#### `runtime.background_task_failed`

- `task_id`
- `parent_session_id`
- `child_session_id`（可选；如果失败发生在 child session 建立之前可为空）
- `status: "failed"`
- `error`
- `result_available: true`

#### `runtime.background_task_cancelled`

- `task_id`
- `parent_session_id`
- `child_session_id`（可选；若 child session 尚未创建可为空）
- `status: "cancelled"`
- `error`（可选）
- `result_available: false`

#### `runtime.background_task_waiting_approval`

- `task_id`
- `parent_session_id`
- `child_session_id`
- `status: "running"`
- `approval_blocked: true`

这里的 `status: "running"` 明确表示：approval-blocked 是 child session lifecycle 的派生观察结果，而不是对 task status 词汇表的扩展。

对于最小契约，`runtime.background_task_waiting_approval` 不再单独引入新的 `approval_session_id` 标识符；当前语义直接使用 `child_session_id` 指向进入 `waiting` 的 child session。

## 顺序规则

通知事件以 **parent session** 为作用域，并继续服从现有 session event ordering 模型。

要求：

1. 通知事件使用 parent session 自己的 sequence 空间
2. parent session 内 sequence 继续单调递增
3. 通知顺序反映 runtime 提交生命周期真相的顺序，而不是客户端收到事件的时机
4. 如果某个通知同时带有 `result_available`，则该字段不得早于其所依赖的生命周期真相被持久化

## 去重规则

leader notification 必须满足：**对同一语义转换至多投递一次**。

最小要求：

- runtime 为每种通知语义持久化内部 delivery markers

例如：

- completed 通知仅发出一次
- failed 通知仅发出一次
- cancelled 通知仅发出一次
- approval-blocked 通知在当前 waiting 状态下仅发出一次

重启后，runtime 必须依据持久化的 notification delivery state，避免把同一条通知再次写入 parent session。

> 这里的 delivery state 属于 runtime 内部持久化真相，不要求出现在 `BackgroundTaskResult` 这样的 leader-facing retrieval payload 中。

## 恢复语义

恢复是必需的，因为 parent 或 runtime 可能在 child 完成后、leader 消费前重启。

要求：

1. child task 先持久化自己的 lifecycle truth
2. 通知投递状态也作为 runtime truth 持久化，而不是依赖内存回调
3. 重启后 runtime 能判断 leader 是否已经被通知
4. 如果 lifecycle truth 已存在、但通知尚未完成提交，则 runtime 在 reconciliation 中补全通知投递
5. parent session 的 `resume(session_id)` 必须像其他 session event 一样暴露这些已投递通知

## Approval-blocked 语义

approval-blocked 不是 terminal task status，但它对 leader 是重要事件。

要求：

- 当 child session 进入 `waiting` 时，runtime 向 parent session 发出 `runtime.background_task_waiting_approval`
- leader 可通过 `child_session_id` 检查进入 `waiting` 的 child session
- 通知不得通过普通文本输出注入来伪装实现

## Polling 与 Notification 的关系

Polling 可以存在，但不能成为唯一模型。

建议的契约拆分：

- `load_background_task_result(task_id)` = pull surface
- parent-session notification events = push surface

clients、hooks 与未来 async orchestration 可以选择其一或同时使用，但它们都必须建立在同一层 runtime truth 之上。

## Hook 与 Client 的含义

本 issue 不应把 hooks 变成真相源。

正确顺序应是：

- runtime 先发出并持久化通知真相
- hooks 作为可选观察者消费这些生命周期时刻
- Web / TUI / SSE 在 parent session 上直接渲染这些 runtime events，而不是引入自己的并行通知模型

## 建议实现顺序

为了让 #139 保持可执行且范围收敛，建议按如下顺序落地：

1. 为 background-task state 增加 `parent_session_id`
2. 定义并持久化 notification delivery state（内部真相，不直接暴露到 leader-facing payload）
3. 增加 `load_background_task_result(task_id)`
4. 稳定化并发射 parent-session background-task notification events
5. 让 HTTP / stream / client surfaces 消费这层已有 runtime truth

## 验收检查点

issue #139 只有在以下条件全部成立时才算完成：

1. leader 能启动一个带 notification target 的后台任务。
2. 当 child task 完成、失败、取消或进入 approval-blocked 状态时，parent session 会收到且只收到一条对应的 runtime-owned notification event。
3. 调用方可以读取结构化后台任务结果，而不是靠 prompt 文本 scraping。
4. 调用方可以通过 `resume(child_session_id)` 恢复完整 child transcript。
5. 重启 / reconciliation 不会重复投递 leader 通知。
6. parent session 中的通知顺序是确定性的、可 replay 的。

## 超出本 issue 的后续工作

本文档只覆盖 retrieval / notification 这一层。以下内容仍然属于单独 follow-up：

- 更丰富的 child-session lineage / topology 设计
- 完整的 async leader/worker orchestration 语义
- scheduler integration
- UI-specific presentation choices
- 建立在这些事件之上的 richer lifecycle hooks
