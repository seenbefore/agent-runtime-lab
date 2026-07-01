# Agent Runtime Lab 架构设计

## 目标

构建一个最小可观察的 Agent Runtime。

第一版系统需要做到：

- 接收一个用户任务
- 创建一次 Run
- 运行最小 Agent Loop
- 让模型生成下一步决策
- Runtime 根据决策调用工具
- 保存每一步执行 trace
- 输出最终结果
- 通过 API 查看完整 Run 记录

一句话目标：

> 一个 HTTP 请求触发一次 Agent Run，Agent 至少调用一个本地工具，所有步骤被持久化，并且可以通过 `GET /runs/{run_id}` 完整复盘。

## 非目标

第一版不做以下内容：

- 多 Agent 编排
- 异步任务队列
- 前端 UI
- 用户认证
- 长期记忆
- 插件系统
- 自动写文件
- 自动修改代码
- `write_file`
- `apply_patch`
- 任意 shell 执行
- 复杂权限系统
- 数据库存储

第一版只关注最小闭环，不追求 Agent 能力完整。

## 核心领域模型

### Task

`Task` 是用户提交的任务内容。

示例：

```json
{
  "task": "请查看 README.md，并告诉我这个项目怎么运行"
}
```

### Run

`Run` 表示一次任务执行记录。

同一个 Task 可以被执行多次，每次执行都是一个独立的 Run。

最小字段：

```json
{
  "id": "run_xxx",
  "task": "用户提交的任务",
  "status": "running",
  "steps": [],
  "result": null,
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

字段含义：

- `id`：这次执行的唯一标识
- `task`：用户提交的任务
- `status`：执行状态
- `steps`：执行过程中的事件列表
- `result`：最终结果
- `error`：失败原因
- `created_at`：创建时间
- `updated_at`：更新时间

### Step

`Step` 表示 Run 过程中的一条事件记录。

最小字段：

```json
{
  "index": 1,
  "type": "model_decision",
  "data": {},
  "created_at": "..."
}
```

字段含义：

- `index`：这是第几步
- `type`：事件类型
- `data`：事件内容
- `created_at`：事件发生时间

## Step 类型

第一版支持以下 Step 类型：

### model_decision

模型这一轮输出的决策。

示例：

```json
{
  "type": "model_decision",
  "data": {
    "action": "read_file",
    "args": {
      "path": "README.md"
    }
  }
}
```

### tool_call

Runtime 实际允许并调用了某个工具。

示例：

```json
{
  "type": "tool_call",
  "data": {
    "tool": "read_file",
    "args": {
      "path": "README.md"
    }
  }
}
```

### tool_result

工具执行后返回的结果。

示例：

```json
{
  "type": "tool_result",
  "data": {
    "tool": "read_file",
    "status": "success",
    "data": {
      "path": "README.md",
      "exists": true,
      "content": "..."
    },
    "error": null
  }
}
```

### final

模型返回最终答案，Run 正常完成。

示例：

```json
{
  "type": "final",
  "data": {
    "content": "这个项目通过 uvicorn app.main:app --reload 启动"
  }
}
```

### error

Runtime 拒绝执行，或者发生不可恢复错误。

示例：

```json
{
  "type": "error",
  "data": {
    "message": "Tool not allowed: delete_file"
  }
}
```

## Run 状态机

第一版只支持三个状态：

```text
running
completed
failed
```

状态迁移：

```text
创建 Run
-> running

模型返回 final
-> completed

协议错误 / 非法工具 / 参数非法 / 超过 max_steps
-> failed
```

第一版不支持：

```text
pending
paused
cancelled
retrying
```

## Agent Decision 协议

模型不能直接调用工具。

模型只能输出结构化决策，由 Runtime 解析、校验并执行。

第一版模型输出只允许两种形式。

### 调用工具

```json
{
  "action": "read_file",
  "args": {
    "path": "README.md"
  }
}
```

### 输出最终答案

```json
{
  "final": "最终答案"
}
```

协议规则：

- 模型输出必须是合法 JSON
- 输出必须符合上述两种结构之一
- 如果是 `action`，必须包含 `args`
- 即使工具没有参数，也必须返回 `"args": {}`
- 如果协议不合法，记录 `error`，并将 Run 标记为 `failed`

## Agent Loop

最小 Agent Loop：

```text
1. 接收 task
2. 创建 Run，status=running
3. 进入循环，最多执行 max_steps 次
4. 将 task、已有 steps、allowed_tools 发送给模型
5. 保存模型输出为 model_decision step
6. 如果模型返回 final：
   - 保存 final step
   - 设置 Run.status=completed
   - 保存 Run.result
   - 结束 loop
7. 如果模型返回 action：
   - 检查 action 是否在 allowed_tools 中
   - 检查 args 是否合法
8. 如果检查失败：
   - 保存 error step
   - 设置 Run.status=failed
   - 保存 Run.error
   - 结束 loop
9. 如果检查通过：
   - 保存 tool_call step
   - 执行工具
   - 保存 tool_result step
   - 进入下一轮
10. 如果超过 max_steps：
   - 保存 error step
   - 设置 Run.status=failed
   - 保存 Run.error="max steps exceeded"
```

## Runtime 边界规则

第一版最重要的两个 Runtime 控制：

```text
max_steps
allowed_tools
```

### max_steps

限制一次 Run 最多允许模型决策多少轮。

目的：

```text
防止 Agent 无限循环。
```

第一版可以设置为：

```text
max_steps = 8
```

### allowed_tools

限制模型可以请求哪些工具。

第一版允许：

```text
read_file
search_code
run_tests
```

如果模型请求不在 `allowed_tools` 中的工具：

```text
记录 model_decision
记录 error
Run.status = failed
不记录 tool_call
不执行工具
```

规则：

> 只有 `allowed_tools` 中的工具，才可以进入 `tool_call`。

## 工具设计

所有工具返回统一结构：

```json
{
  "tool": "read_file",
  "status": "success",
  "data": {},
  "error": null
}
```

字段含义：

- `tool`：工具名称
- `status`：工具调用状态，取值为 `success` 或 `failed`
- `data`：工具返回的业务结果
- `error`：工具自身无法完成调用时的错误信息

规则：

```text
status=success:
工具完成了这次尝试，并返回可解释结果。

status=failed:
工具自身无法完成调用，或者无法返回可解释结果。

业务结果放在 data。
系统级失败放在 error。
```

### read_file

输入：

```json
{
  "path": "README.md"
}
```

文件存在时输出：

```json
{
  "tool": "read_file",
  "status": "success",
  "data": {
    "path": "README.md",
    "exists": true,
    "content": "..."
  },
  "error": null
}
```

文件不存在时输出：

```json
{
  "tool": "read_file",
  "status": "success",
  "data": {
    "path": "README.md",
    "exists": false,
    "content": null
  },
  "error": null
}
```

路径越权时输出：

```json
{
  "tool": "read_file",
  "status": "failed",
  "data": null,
  "error": "Path escapes workspace"
}
```

### search_code

输入：

```json
{
  "query": "FastAPI"
}
```

输出：

```json
{
  "tool": "search_code",
  "status": "success",
  "data": {
    "matches": [
      {
        "path": "app/main.py",
        "line": 12,
        "text": "app = FastAPI()"
      }
    ]
  },
  "error": null
}
```

没有匹配结果时：

```json
{
  "tool": "search_code",
  "status": "success",
  "data": {
    "matches": []
  },
  "error": null
}
```

搜索工具自身异常时：

```json
{
  "tool": "search_code",
  "status": "failed",
  "data": null,
  "error": "rg not found"
}
```

### run_tests

输入：

```json
{
  "target": null
}
```

含义：

- `target=null`：运行全部测试
- `target="tests/test_api.py"`：运行指定测试目标

输出：

```json
{
  "tool": "run_tests",
  "status": "success",
  "data": {
    "command": "pytest",
    "exit_code": 1,
    "stdout": "...",
    "stderr": "..."
  },
  "error": null
}
```

注意：

```text
exit_code != 0 不代表工具失败。
它表示测试命令正常执行完成，但测试没有通过。
```

如果测试命令无法启动：

```json
{
  "tool": "run_tests",
  "status": "failed",
  "data": null,
  "error": "pytest not found"
}
```

## API 契约

### POST /tasks

提交一个任务，并同步执行一次 Agent Run。

请求：

```json
{
  "task": "请查看 README.md，并告诉我这个项目怎么运行"
}
```

响应：

```json
{
  "run_id": "run_xxx",
  "status": "completed",
  "result": "最终答案",
  "trace_url": "/runs/run_xxx"
}
```

第一版使用同步执行：

```text
请求进入后，直接执行完整 Agent Loop，然后返回结果。
```

暂不做异步队列。

### GET /runs/{run_id}

查看一次 Run 的完整 trace。

响应：

```json
{
  "id": "run_xxx",
  "task": "请查看 README.md，并告诉我这个项目怎么运行",
  "status": "completed",
  "steps": [
    {
      "index": 1,
      "type": "model_decision",
      "data": {
        "action": "read_file",
        "args": {
          "path": "README.md"
        }
      },
      "created_at": "..."
    },
    {
      "index": 2,
      "type": "tool_call",
      "data": {
        "tool": "read_file",
        "args": {
          "path": "README.md"
        }
      },
      "created_at": "..."
    },
    {
      "index": 3,
      "type": "tool_result",
      "data": {
        "tool": "read_file",
        "status": "success",
        "data": {
          "path": "README.md",
          "exists": true,
          "content": "..."
        },
        "error": null
      },
      "created_at": "..."
    },
    {
      "index": 4,
      "type": "model_decision",
      "data": {
        "final": "这个项目通过 ..."
      },
      "created_at": "..."
    },
    {
      "index": 5,
      "type": "final",
      "data": {
        "content": "这个项目通过 ..."
      },
      "created_at": "..."
    }
  ],
  "result": "这个项目通过 ...",
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

## 存储设计

第一版使用 JSON 文件存储。

目录结构：

```text
runs/
  run_xxx.json
```

规则：

```text
一个 Run 对应一个 JSON 文件。
文件名包含 run_id。
每次追加 step 后，将完整 Run 写回文件。
```

最小存储函数：

```text
create_run(task)
append_step(run_id, type, data)
finish_run(run_id, result)
fail_run(run_id, error)
get_run(run_id)
```

Agent Loop 不直接读写 JSON 文件，只通过 storage 函数访问 Run。

这样可以隔离执行逻辑和存储细节。后续如果从 JSON 文件切换到 SQLite，Agent Loop 不需要大改。

## 最小验收标准

输入一个任务：

```text
请查看 README.md，并告诉我这个项目怎么运行。
```

系统应该完成：

```text
1. 创建 Run
2. 模型生成至少一个 decision
3. Runtime 调用至少一个工具
4. 保存 model_decision step
5. 保存 tool_call step
6. 保存 tool_result step
7. 保存 final step
8. Run.status=completed
9. Run.result 有最终答案
10. GET /runs/{run_id} 能看到完整 trace
```

最小成功 trace：

```text
model_decision
tool_call
tool_result
model_decision
final
```

## 后续演进

第一版完成后，可以继续演进：

```text
MVP-1:
- 接入 apply_patch
- 增加 diff preview
- 增加写入前确认

MVP-2:
- 异步任务执行
- GET /runs/{run_id} 查看运行中 trace
- 支持取消任务

MVP-3:
- SQLite 存储
- Trace 查询
- 多模型支持
- Web UI
```

当前阶段只实现 MVP-0：

```text
可观察的最小 Agent Runtime。
```
