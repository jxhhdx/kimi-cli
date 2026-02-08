# Kimi CLI 魔改版 - AI 开发指南

> **项目目标**: 基于官方 kimi-cli 进行魔改，添加任务完成通知和邮件接收处理功能
> **官方源码**: `/Users/gaoxiang/Workspace2026/kimi-cli`
> **本目录**: `/Users/gaoxiang/Workspace2026/SoftwareDesign/kimi-cli`（工作记录和脚本）
> **开发状态**: Phase 1 进行中

---

## 📁 目录结构说明

```
/Users/gaoxiang/Workspace2026/SoftwareDesign/kimi-cli/  (本目录 - 工作区)
├── AGENTS.md              # 本文件 - 项目指南
├── WORK_LOG.md            # 工作日志 - 每天做了什么
├── CURRENT_STATUS.md      # 当前状态 - 下一步做什么
├── docs/                  # 设计文档
│   ├── security-design.md # 安全策略设计
│   └── architecture.md    # 架构设计（待创建）
├── scripts/               # 工具脚本
│   ├── kimi-cli-manager.sh    # 版本管理器
│   ├── install-custom.sh      # 安装脚本
│   └── docker/                # Docker测试环境
│       └── docker-compose.test.yml
└── src/                   # 源码（将在官方代码基础上创建）
    └── kimi_cli_custom/   # 魔改模块

/Users/gaoxiang/Workspace2026/kimi-cli/  (官方源码 - 只读参考)
├── src/kimi_cli/          # 官方源码
├── pyproject.toml
└── ...
```

---

## 🎯 核心功能

### 1. 任务完成钩子系统
- 在 kimi 完成任务后触发通知
- 支持邮件、Webhook、钉钉等多种通知方式
- 配置驱动，支持并行执行

### 2. 邮件接收处理
- **常驻模式**: `kimi mail-server` 后台监听 IMAP
- **按需模式**: `kimi mail-check` 手动检查新邮件
- **安全策略**: 白名单 + 指令白名单 + 敏感操作确认

### 3. 版本管理
- `kimi-cli-manager` 脚本管理官方版/魔改版切换
- 支持快速回退、合并官方更新

---

## 🚀 快速上手（新 AI 接入）

### 第一步：了解当前状态
```bash
# 查看当前进度
cat /Users/gaoxiang/Workspace2026/SoftwareDesign/kimi-cli/CURRENT_STATUS.md

# 查看详细工作日志
cat /Users/gaoxiang/Workspace2026/SoftwareDesign/kimi-cli/WORK_LOG.md
```

### 第二步：查看官方源码结构
```bash
cd /Users/gaoxiang/Workspace2026/kimi-cli

# 关键文件
src/kimi_cli/cli/__init__.py      # CLI入口，_post_run()是钩子集成点
src/kimi_cli/app.py               # KimiCLI类，核心逻辑
src/kimi_cli/config.py            # 配置系统
src/kimi_cli/ui/print/__init__.py # --print模式，支持后台执行
```

### 第三步：继续开发
根据 CURRENT_STATUS.md 中的"下一步任务"继续开发。

---

## 🏗️ 架构设计

### 钩子系统集成点
```python
# 修改位置: src/kimi_cli/cli/__init__.py 的 _post_run() 函数

async def _post_run(last_session: Session, succeeded: bool) -> None:
    # ... 原有代码 ...
    
    # NEW: 触发任务完成钩子
    from kimi_cli.hooks import get_hook_manager
    await get_hook_manager().trigger_all(context)
```

### 邮件接收流程
```
新邮件到达 → 安全验证(白名单/DKIM) → 解析任务 → 判断执行模式
                                           ↓
              只读操作(/review) → 自动执行 → 发送结果邮件
              写操作(/code)   → 发送确认邮件 → 等待用户确认 → 执行
```

---

## ⚙️ 配置示例

```toml
# ~/.kimi/config.toml

[hooks.task_completion]
enabled = true

[[hooks.task_completion.channels]]
type = "email"
smtp_host = "smtp.gmail.com"
username = "your@gmail.com"
password = "${GMAIL_APP_PASSWORD}"
to = "receiver@example.com"

[inbound_mail]
enabled = true
server = "imap.gmail.com"
username = "your@gmail.com"
password = "${IMAP_PASSWORD}"

whitelist = [
    { email = "colleague@company.com", dkim_required = true }
]
```

---

## 🧪 测试环境

```bash
# 启动测试邮件服务器
cd /Users/gaoxiang/Workspace2026/SoftwareDesign/kimi-cli
docker-compose -f scripts/docker/docker-compose.test.yml up -d

# 测试账户
# SMTP: localhost:3025, user=test@localhost, pass=test
# IMAP: localhost:3143, user=test@localhost, pass=test
```

---

## 📝 开发规范

1. **代码修改**: 尽量使用 monkey-patch 或插件机制，少改官方代码
2. **配置驱动**: 所有功能都可通过 `~/.kimi/config.toml` 配置
3. **错误隔离**: 钩子失败不影响主流程
4. **测试覆盖**: 新增功能必须有单元测试

---

## 🔗 相关链接

- 官方仓库: https://github.com/moonshot-ai/kimi-cli
- 设计文档: ./docs/security-design.md

---

*最后更新: 2026-02-08*
