# 面向客户端的运行时 API 契约

来源 Issue：#14

## 目的

定义客户端与无头运行时（Headless runtime）之间的 MVP 契约，用于运行请求、列出会话、加载会话状态、恢复会话以及订阅事件流。

## 状态

当前的契约已经通过 CLI、运行时方法以及极简 HTTP 层落地。HTTP 路径目前覆盖会话列表、会话重放、流式运行和审批处理，但客户端体验仍在继续完善。

## 当前运行时请求/响应形状

源自 `src/voidcode/runtime/contracts.py`：

```python
RuntimeRequest(
    prompt: str,
    session_id: str | None = None,
    metadata: dict[str, object] = {},
)

RuntimeResponse(
    session: SessionState,
    events: tuple[EventEnvelope, ...] = (),
    output: str | None = None,
)
```

## 会话形状

源自 `src/voidcode/runtime/session.py`：

```python
SessionState(
    session: SessionRef(id: str),
    status: Literal["idle", "running", "waiting", "completed", "failed"],
    turn: int,
    metadata: dict[str, object],
)

StoredSessionSummary(
    session: SessionRef(id: str),
    status: SessionStatus,
    turn: int,
    prompt: str,
    updated_at: int,
)
```

## MVP 客户端操作

### 运行请求 (Run request)

输入：
- `prompt`
- 可选的 `session_id`
- 可选的客户端/运行时元数据

输出：
- 最终的 `session`
- 有序的 `events`
- 最终的 `output`

当前实现层面：
- 运行时：`VoidCodeRuntime.run(request)`
- CLI：`voidcode run <request> [--workspace] [--session-id]`

### 列出持久化会话 (List persisted sessions)

输出：
- `StoredSessionSummary` 的元组/列表

当前实现层面：
- 运行时：`VoidCodeRuntime.list_sessions()`
- CLI：`voidcode sessions list [--workspace]`

### 恢复持久化会话 (Resume persisted session)

输入：
- `session_id`

输出：
- 存储的该会话重放的 `RuntimeResponse`

当前实现层面：
- 运行时：`VoidCodeRuntime.resume(session_id)`
- CLI：`voidcode sessions resume <session_id> [--workspace]`

## 会话生命周期

MVP 生命周期：

1. 客户端提交一个运行请求
2. 运行时创建或重用一个会话 ID
3. 运行时在轮次中发出有序事件
4. 运行时终结一个响应
5. 运行时持久化会话摘要、事件和输出
6. 客户端后续可以列出或恢复会话

## 当前持久化会话行为

目前的实现可以持久化足以支持以下操作的数据：

- `sessions list` 返回 `StoredSessionSummary`
- `sessions resume <id>` 重放存储的响应

目前的集成测试验证了恢复（resume）会返回存储的输出和会话的存储事件序列。

## API 不变量

- 客户端必须将运行时视为系统边界
- 客户端不直接调用工具
- 客户端不创建与持久化的运行时状态相背离的私有会话状态
- 恢复（resume）返回可重放的、已存储的响应，而非根据 UI 状态推断出的重建版本
- 客户端必须按交付顺序处理运行时事件，即使未来的图模式在现有阶段之间插入额外事件
- 客户端必须能够容忍新增的有序事件，而不能假设当前的确定性事件序列已经穷尽所有情况

## 当前 HTTP/流式传输映射

现有 HTTP 层保留了相同的操作边界：

- 运行/创建会话
- 列出会话
- 加载/恢复会话
- 订阅或接收运行时的有序事件

本文档有意地将契约定义与具体的 FastAPI/Starlette 路由细节解耦。当前的确定性事件序列仍然是规范基线；未来的图模式可以在现有阶段之间增加有序事件，但不应改变这些 API 边界。

## 非目标

- 完整的传输层实现
- post-MVP 的多智能体会话拓扑
- 特定于供应商的请求格式

## 验收检查点

- TUI 和 Web 客户端可以在不绕过运行时方法或概念的情况下实现
- 可以使用稳定的会话摘要和存储响应形状来列出和恢复持久化的会话
- 未来的 API 路由可以直接映射到这些操作上，而无需更改语义
