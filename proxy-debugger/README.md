# Proxy Debugger

一个独立于作业评分系统的 OpenAI-compatible 代理接口测试工具。

它用于验证代理服务是否正确支持：

- `/v1/responses`
- `/v1/chat/completions`

并自动保存：

- 原始请求
- 原始响应
- 提取出的文本
- 诊断结果
- 耗时与状态码

## 安装

建议在单独虚拟环境中使用：

```powershell
cd proxy-debugger
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 配置

复制一份示例配置：

```powershell
Copy-Item config.example.yaml config.yaml
```

然后修改 `config.yaml` 中的内容。

## 用法

单次测试 `responses`：

```powershell
python run_test.py single --endpoint responses --prompt "请只回复：你好"
```

单次测试 `chat.completions`：

```powershell
python run_test.py single --endpoint chat --prompt "请只回复：你好"
```

对比两个 endpoint：

```powershell
python run_test.py compare --prompt "请只回复：你好"
```

执行内置健康检查：

```powershell
python run_test.py suite --name smoke
```

执行 JSON 输出检查：

```powershell
python run_test.py suite --name json
```

连续压测：

```powershell
python run_test.py suite --name stress --repeat 5
```

## 输出

每次运行会在 `outputs/` 下保存一个 JSON 文件，包含：

- `request`
- `response`
- `parsed_text`
- `diagnostics`
- `status_code`
- `elapsed_ms`

如果代理服务出现类似下面的问题，这个工具会明确标出来：

- `completed_but_empty_output`
- `tokens_present_but_no_text`
- `chat_content_null`
- `non_standard_response_shape`
- `transport_error`

## 目录结构

```text
proxy-debugger/
  README.md
  requirements.txt
  config.example.yaml
  run_test.py
  src/
    __init__.py
    client.py
    diagnostics.py
    extractors.py
    reporters.py
    scenarios.py
```
