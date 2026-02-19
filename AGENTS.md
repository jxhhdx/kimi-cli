# Kimi Code CLI - AI 代理开发指南

> **版本**: 1.9.0+custom  
> **最后更新**: 2026-02-19  
> **用途**: 本指南面向在 Kimi Code CLI 项目上工作的 AI 编码代理。

---

## 1. 项目概述

Kimi Code CLI 是一个 AI 驱动的终端代理，可协助软件开发任务。它能够：

- 读取和编辑代码文件
- 执行 shell 命令
- 搜索和获取网页内容
- 在执行过程中自主规划和调整操作
- 通过 ACP（Agent Client Protocol）与 IDE 集成
- 支持 MCP（Model Context Protocol）工具

本仓库包含官方 Kimi CLI 的**定制版本**，具有以下额外功能：
- **任务完成钩子**: 任务完成时自动通知（邮件、Webhook）
- **邮件接收处理**: 通过电子邮件（IMAP）接收和处理任务

---

## 2. 技术栈

### 核心技术
| 组件 | 技术 | 版本 |
|-----------|------------|---------|
| 语言 | Python | >=3.10 (开发: 3.14) |
| 包管理器 | uv | 最新版 |
| 构建后端 | uv_build | 0.8.x |
| CLI 框架 | typer | 0.21.1 |
| HTTP 客户端 | aiohttp | 3.13.3, httpx | 
| LLM 抽象层 | kosong | 工作空间 |
| 异步 SSH/文件操作 | kaos (pykaos) | 工作空间 |
| Web 框架 | FastAPI | >=0.115.0 |
| 前端 | React + Vite + TypeScript | React 19 |

### 主要依赖
- **LLM/AI**: `anthropic`, `google-genai`, `openai`, `pydantic`
- **MCP**: `fastmcp`, `mcp`
- **异步**: `aiofiles`, `aioimaplib` (IMAP), `aiosmtplib` (SMTP)
- **UI**: `rich`, `prompt-toolkit`, `pillow`
- **数据**: `pyyaml`, `tomlkit`, `jinja2`
- **安全**: `keyring` 用于凭证存储

---

## 3. 项目结构

```
/Users/gaoxiang/Workspace2026/kimi-cli/          # 项目根目录
├── src/kimi_cli/               # 主 CLI 源代码
│   ├── cli/                    # CLI 命令和入口点
│   │   ├── __init__.py         # 主 CLI (kimi 命令), 钩子集成
│   │   ├── mail.py             # 邮件子命令 (check/server/test)
│   │   ├── mcp.py              # MCP 服务器管理
│   │   ├── web.py              # Web UI 子命令
│   │   └── ...
│   ├── hooks/                  # 定制: 任务完成钩子
│   │   ├── base.py             # HookManager, TaskContext, HookConfig
│   │   └── notify/
│   │       ├── email.py        # SMTP 邮件通知
│   │       └── webhook.py      # Slack/Discord Webhooks
│   ├── mail/                   # 定制: 入站邮件处理
│   │   ├── client.py           # 异步 IMAP 客户端
│   │   ├── parser.py           # 邮件解析
│   │   ├── security.py         # 安全验证
│   │   └── models.py           # 邮件数据模型
│   ├── soul/                   # Agent 核心逻辑
│   │   ├── agent.py            # Agent 运行时和执行
│   │   ├── kimisoul.py         # 主 Agent 循环
│   │   ├── context.py          # 对话上下文
│   │   └── toolset.py          # 工具注册
│   ├── tools/                  # 内置工具
│   │   ├── file/               # 文件操作 (read, write, replace)
│   │   ├── shell/              # Shell 执行
│   │   ├── web/                # Web 搜索/获取
│   │   └── multiagent/         # 子代理创建和任务分配
│   ├── ui/                     # 用户界面
│   │   ├── shell/              # 交互式终端 UI
│   │   ├── print/              # 非交互式打印模式
│   │   └── acp/                # ACP 服务器 UI
│   ├── web/                    # Web UI 后端 (FastAPI)
│   │   ├── api/                # REST API 端点
│   │   ├── runner/             # 会话工作进程
│   │   └── app.py              # FastAPI 应用
│   ├── acp/                    # Agent Client Protocol 实现
│   ├── wire/                   # Wire 协议（内部 IPC）
│   ├── config.py               # 配置模型和加载
│   ├── app.py                  # KimiCLI 主应用类
│   └── session.py              # 会话管理
├── packages/                   # 工作空间包
│   ├── kosong/                 # LLM 抽象层
│   ├── kaos/                   # 异步文件/SSH 操作
│   └── kimi-code/              # Kimi Code 专用代码
├── sdks/kimi-sdk/              # Kimi Code 的 Python SDK
├── web/                        # Web UI 前端 (React + Vite)
│   ├── src/                    # React 源码
│   ├── package.json            # npm 依赖
│   └── vite.config.ts          # Vite 配置
├── tests/                      # 单元测试
├── tests_e2e/                  # 端到端测试
├── tests_custom/               # 定制: 定制功能测试
├── docs/                       # VitePress 文档
├── scripts/                    # 构建和工具脚本
├── pyproject.toml              # 主项目配置
├── Makefile                    # 构建自动化
└── kimi.spec                   # PyInstaller 二进制构建配置
```

---

## 4. 构建和开发命令

### 初始设置
```bash
# 准备开发环境（安装依赖 + hooks）
make prepare

# 或手动执行:
uv sync --frozen --all-extras --all-packages
uv tool install prek
uv tool run prek install
```

### 运行 CLI
```bash
# 以开发模式运行
uv run kimi

# 使用特定选项运行
uv run kimi --yolo --prompt "Hello"
uv run kimi --print --prompt "Review src/main.py"

# 运行 Web UI 后端
make web-back

# 运行 Web UI 前端（需要 Node.js）
make web-front
```

### 代码质量
```bash
# 格式化所有代码
make format              # 所有包
make format-kimi-cli     # 仅主 CLI
make format-kosong       # 仅 kosong
make format-pykaos       # 仅 kaos
make format-web          # Web 前端

# 运行 lint 和类型检查
make check               # 所有包
make check-kimi-cli      # 仅主 CLI
make check-kosong        # 仅 kosong
make check-pykaos        # 仅 kaos
make check-web           # Web 前端（需要 Node.js）
```

### 测试
```bash
# 运行所有测试
make test

# 运行特定测试套件
make test-kimi-cli       # 主 CLI 测试 (tests/ + tests_e2e/)
make test-kosong         # Kosong 包测试
make test-pykaos         # Kaos 包测试
make test-kimi-sdk       # SDK 测试

# 直接使用 pytest 运行以获得更精细控制
uv run pytest tests -vv
uv run pytest tests_e2e -vv
```

### 构建
```bash
# 构建 Python 包（用于分发）
make build               # 所有包
make build-kimi-cli      # CLI + kimi-code 包
make build-kosong        # Kosong 包
make build-pykaos        # Kaos 包
make build-kimi-sdk      # SDK 包

# 构建 Web UI（嵌入到 Python 包中）
make build-web

# 构建独立二进制文件
make build-bin           # 单文件可执行程序
make build-bin-onedir    # 单目录分发
```

### AI 驱动的任务
```bash
# 从最近的提交生成变更日志
make gen-changelog

# 生成用户文档
make gen-docs

# 运行 AI 测试套件
make ai-test
```

---

## 5. 架构

### 核心组件

#### 1. 会话管理 (`session.py`)
- 会话与工作目录绑定
- 每个会话有唯一的 UUID
- 上下文存储在 `context.jsonl` 中
- Wire 协议日志存储在 `wire.jsonl` 中

#### 2. Agent 执行 (`soul/`)
- `KimiSoul`: 主 Agent 协调器
- `Runtime`: 执行环境和工具注册表
- `Agent`: 系统提示词和工具集容器
- `Context`: 消息历史管理

#### 3. 工具 (`tools/`)
所有工具继承自 `BaseTool` 并在 `KimiToolset` 中注册：
- **文件**: `ReadFile`, `WriteFile`, `StrReplaceFile`, `Glob`, `Grep`
- **Shell**: `Shell` (bash/PowerShell)
- **Web**: `SearchWeb`, `FetchURL`
- **多 Agent**: `CreateSubagent`, `Task`
- **工具**: `Think`, `SetTodoList`

#### 4. UI 模式 (`ui/`)
- **Shell**: 带键盘快捷键的交互式终端
- **Print**: 用于脚本/管道的非交互式
- **ACP**: Agent Client Protocol 服务器
- **Wire**: 实验性 wire 协议

#### 5. Web UI (`web/`)
- 支持 WebSocket 的 FastAPI 后端
- 使用 Radix UI 组件的 React 前端
- 通过 REST API 管理会话
- 通过 WebSocket 实时更新

### 定制功能

#### 任务完成钩子 (`hooks/`)
钩子在 `_post_run()` 中任务完成后触发（见 `cli/__init__.py`）：

```python
# 钩子执行流程
任务完成 → _post_run() → HookManager.trigger_all()
                            → EmailHook.send()
                            → WebhookHook.post()
```

在 `~/.kimi/config.toml` 中配置：
```toml
[hooks.task_completion]
enabled = true

[[hooks.task_completion.channels]]
type = "email"
smtp_host = "smtp.gmail.com"
username = "your@gmail.com"
password = "${GMAIL_APP_PASSWORD}"  # 环境变量引用
to = "receiver@example.com"
```

#### 邮件接收处理 (`mail/`)
邮件处理流程：
```
IMAP IDLE/新邮件 → 解析邮件 → 安全验证 → 执行任务 → 发送结果
                          ↓
                    白名单检查
                    DKIM 验证（计划中）
                    命令模式匹配
```

CLI 命令：
```bash
kimi mail test         # 测试邮件配置
kimi mail check        # 检查邮件（一次）
kimi mail server       # 启动 IMAP IDLE 服务器
```

---

## 6. 测试策略

### 测试组织
| 目录 | 用途 |
|-----------|---------|
| `tests/` | 核心功能单元测试 |
| `tests_e2e/` | 端到端测试，包括 Wire 协议 |
| `tests_custom/` | 定制功能测试（hooks、mail） |
| `tests_ai/` | AI 驱动的测试套件 |
| `packages/*/tests/` | 工作空间包测试 |

### 运行测试
```bash
# 标准测试运行
uv run pytest tests -vv

# 带覆盖率（示例）
uv run pytest tests --cov=kimi_cli --cov-report=html

# E2E 测试（可能需要特定设置）
uv run pytest tests_e2e -vv
```

### 测试 Fixtures (`tests/conftest.py`)
可用的关键 fixtures：
- `temp_work_dir`: 隔离的工作目录
- `session`: Mock 会话实例
- `runtime`: 带有 Mock LLM 的完整运行时
- 各种工具 fixtures (`read_file_tool`, `shell_tool`, 等)

---

## 7. 代码风格指南

### Python
- **格式化工具**: ruff（行长度 100）
- **类型检查器**: pyright（src/ 使用严格模式）
- **Linter**: ruff（E, F, UP, B, SIM, I 规则）

### 导入排序
```python
from __future__ import annotations  # 始终放在第一位

# 标准库
import asyncio
from pathlib import Path

# 第三方
import typer
from pydantic import BaseModel

# 工作空间包
from kaos.path import KaosPath
from kosong.message import Message

# 本地模块
from kimi_cli.config import Config
from kimi_cli.utils.logging import logger
```

### 类型提示
- 使用 Python 3.10+ 语法: `str | None`, `list[str]`
- 使用 `from __future__ import annotations` 处理前向引用
- 配置/数据类使用 Pydantic 模型

### 文档
- 公共 API 需要 Docstrings
- 复杂逻辑需要注释
- 保持英文（作为权威来源）

---

## 8. 配置

### 用户配置 (`~/.kimi/config.toml`)
```toml
default_model = "kimi-k2.5"
default_thinking = false

[models.kimi-k2.5]
provider = "kimi"
model = "kimi-k2.5"
max_context_size = 256000

[providers.kimi]
type = "kimi"
base_url = "https://api.kimi.com/coding/v1"
api_key = "sk-..."

[loop_control]
max_steps_per_turn = 100
max_retries_per_step = 3

# 定制: Hooks 配置
[hooks.task_completion]
enabled = true

# 定制: 入站邮件配置
[inbound_mail]
enabled = false
server = "imap.gmail.com"
username = "your@gmail.com"
password = "${IMAP_PASSWORD}"
```

### 环境变量
| 变量 | 用途 |
|----------|---------|
| `KIMI_API_KEY` | 覆盖 API 密钥 |
| `KIMI_BASE_URL` | 覆盖 API 基础 URL |
| `KIMI_MODEL_NAME` | 覆盖模型名称 |
| `KIMI_SHARE_DIR` | 覆盖数据目录 (~/.kimi) |
| `KIMI_EMAIL_*` | 邮件配置（定制功能） |

---

## 9. 安全注意事项

### 内置安全
- **审批系统**: 敏感操作需要用户确认（除非使用 `--yolo`）
- **路径限制**: 工具仅在工作目录内操作
- **Shell 限制**: 危险命令可被阻止

### 定制功能安全 (`mail/security.py`)
- **白名单**: 只有配置的电子邮件地址可以触发任务
- **DKIM 验证**: 计划用于邮件真实性验证
- **命令白名单**: 限制可以通过邮件使用的斜杠命令
- **沙箱模式**: 邮件触发的任务以受限权限运行

### 安全配置
- API 密钥尽可能通过 `keyring` 存储
- OAuth 令牌绝不存储在配置文件中
- 密码支持环境变量引用: `${VAR_NAME}`

---

## 10. 开发工作流

### 添加新工具
1. 在 `src/kimi_cli/tools/<category>/` 中创建类
2. 继承自 `BaseTool` 或适当的基类
3. 定义 `name`, `description`, `parameters` 模式
4. 实现 `execute()` 方法
5. 在 `KimiToolset` 中注册
6. 在 `tests/tools/` 中添加测试

### 添加新钩子类型
1. 在 `hooks/` 中创建继承自 `TaskCompletionHook` 的类
2. 实现 `on_complete(context)` 方法
3. 如需要添加配置模型
4. 在 `hooks/__init__.py` 的 `register_default_hooks()` 中注册

### 修改 CLI 命令
1. 编辑 `src/kimi_cli/cli/` 中的适当文件
2. 使用 `typer` 定义命令
3. 在 `cli/__init__.py` 中通过 `cli.add_typer()` 添加到主 CLI

---

## 11. 常见问题

### 构建问题
```bash
# 如果 uv sync 失败
rm -rf .venv uv.lock
uv sync --all-extras --all-packages

# 如果 web 构建失败
npm --prefix web install
make build-web
```

### 测试问题
```bash
# 如果测试因缺少依赖而失败
make prepare

# 如果更改后类型检查失败
make format && make check
```

### 运行时问题
- 检查日志: `~/.kimi/logs/kimi.log`
- 启用调试模式: `kimi --debug`
- 验证配置: `kimi info config`

---

## 12. 资源

### 文档
- **用户文档**: https://moonshotai.github.io/kimi-cli/en/
- **中文文档**: https://moonshotai.github.io/kimi-cli/zh/
- **API 文档**: 见 `docs/` 目录（VitePress）

### 关键文件参考
| 文件 | 用途 |
|------|---------|
| `src/kimi_cli/cli/__init__.py` | CLI 入口，钩子集成点 |
| `src/kimi_cli/app.py` | KimiCLI 类，UI 模式运行器 |
| `src/kimi_cli/config.py` | 配置模型 |
| `src/kimi_cli/session.py` | 会话生命周期 |
| `src/kimi_cli/soul/agent.py` | Agent 运行时 |
| `src/kimi_cli/hooks/base.py` | 钩子系统 |
| `src/kimi_cli/mail/client.py` | IMAP 客户端 |

---

*本指南是 Kimi Code CLI 项目的一部分维护。对于官方（非定制）版本，请参见 https://github.com/MoonshotAI/kimi-cli。*
