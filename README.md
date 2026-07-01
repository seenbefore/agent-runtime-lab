# Agent Runtime Lab

最小可观察 Agent Runtime：接收任务，执行 Agent Loop，调用工具，保存 Run/Step trace，并通过 API 查看完整过程。

## 本地启动

```powershell
python -m uvicorn app.main:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

## 本地验收

另开一个终端运行：

```powershell
python scripts/acceptance_check.py
```

脚本会执行：

```text
POST /tasks
GET /runs/{run_id}
```

并打印完整 Run trace。

没有设置 `DEEPSEEK_API_KEY` 时，系统会走 fallback：

```json
{"final": "No model configured"}
```

此时可以验证 API、Run 保存和 trace 查看链路，但不会调用工具。

## DeepSeek 验收

设置环境变量后再启动服务：

```powershell
$env:DEEPSEEK_API_KEY="你的 key"
python -m uvicorn app.main:app --reload
```

然后运行：

```powershell
python scripts/acceptance_check.py --task "请查看 README.md，并告诉我这个项目怎么运行。"
```

期望能在 `GET /runs/{run_id}` 输出中看到类似 trace：

```text
model_decision -> tool_call -> tool_result -> model_decision -> final
```

## 测试

```powershell
python -m pytest tests -v
```
