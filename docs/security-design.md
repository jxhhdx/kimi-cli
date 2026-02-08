# 邮件任务安全设计 - 自由与安全的平衡

## 威胁模型

| 风险 | 场景 | 防护策略 |
|------|------|---------|
| **账号被盗** | 白名单邮箱被盗，发送恶意指令 | 双重验证 + 敏感操作确认 |
| **钓鱼邮件** | 伪造发件人 | SPF/DKIM 验证 + 白名单 |
| **指令注入** | 邮件正文包含危险命令 | 指令白名单 + 沙箱环境 |
| **资源耗尽** | 大文件/长时间任务 | 大小限制 + 超时机制 |
| **信息泄露** | 任务结果发送到错误地址 | 结果只回复发件人 |

---

## 安全策略设计（渐进式）

### Level 1: 基础防护（默认）

```yaml
inbound_mail:
  security_level: "standard"
  
  # 1. 身份验证
  whitelist:
    - email: "colleague@company.com"
      verify_dkim: true  # 强制DKIM验证
      allowed_commands: ["/code", "/review", "/doc"]  # 指令白名单
      max_file_size: "10MB"
      
  # 2. 内容过滤
  content_filter:
    block_patterns:
      - "rm -rf /"        # 危险命令
      - "curl.*\\|.*bash"  # 管道到shell
      - "eval\("           # 代码注入
    require_confirmation:
      - pattern: "delete|remove|rm -"
        reason: "文件删除操作"
      - pattern: "git push.*--force"
        reason: "强制推送"
```

### Level 2: 敏感操作确认（推荐）

对于非只读操作，执行前发送确认邮件：

```
收到任务邮件 → 解析指令 → 识别为敏感操作
                              ↓
                    发送确认邮件给发件人
                    "是否执行：git push --force?"
                    [确认] [取消]
                              ↓
                    收到确认后执行 / 超时取消
```

### Level 3: 完全自动（信任模式）

仅对特定场景开启：

```yaml
inbound_mail:
  security_level: "trusted"
  
  auto_execute_rules:
    - from: "ci@company.com"
      subject_pattern: "^\[DEPLOY\]"
      allowed_working_dirs: ["/home/kimi/deploy"]
      max_execution_time: "5m"
      commands_only: ["/deploy", "/status"]
```

---

## 具体实现建议

### 邮件正文指令解析

支持多种格式：

```
# 格式1: 简洁指令（Subject）
Subject: [AUTO] /review src/main.py

# 格式2: 详细描述（Body）
Subject: [AUTO] Refactor request
Body:
请帮我重构附件中的代码，要求：
1. 使用 asyncio
2. 添加类型注解

附件: refactor.zip

# 格式3: YAML Frontmatter（结构化）
Subject: [AUTO] Task
Body:
---
type: /code
working_dir: /home/kimi/project
auto_approve: false
---

请实现一个邮件解析器...
```

### 指令白名单设计

```python
ALLOWED_COMMANDS = {
    # 只读操作 - 无需确认
    "/review": {"confirm": False, "readonly": True},
    "/doc": {"confirm": False, "readonly": True},
    "/search": {"confirm": False, "readonly": True},
    "/explain": {"confirm": False, "readonly": True},
    
    # 写操作 - 需要确认
    "/code": {"confirm": True, "readonly": False},
    "/refactor": {"confirm": True, "readonly": False},
    "/fix": {"confirm": True, "readonly": False},
    
    # 危险操作 - 禁止或严格确认
    "/git": {"confirm": True, "readonly": False, "allowlist": ["git status", "git log"]},
    "/shell": {"confirm": True, "readonly": False, "restricted": True},
}
```

### 沙箱限制

```python
TASK_SANDBOX = {
    # 工作目录限制
    "allowed_working_dirs": ["/home/kimi/projects/*"],
    "deny_working_dirs": ["/", "/etc", "/home/kimi/.ssh"],
    
    # 执行限制
    "max_execution_time": 600,  # 10分钟
    "max_file_operations": 100,
    "max_files_created": 50,
    
    # 网络限制
    "allow_network": False,  # 邮件触发任务默认禁网
    
    # 工具限制
    "allowed_tools": ["ReadFile", "WriteFile", "StrReplaceFile", "Shell", "Grep"],
    "denied_shell_commands": ["rm -rf", "curl | sh", "wget | sh", "sudo"],
}
```

---

## 测试环境：MailHog + Docker

### 启动命令

```bash
# 启动 MailHog（SMTP:1025, WebUI:8025）
docker run -d \
  --name mailhog \
  -p 1025:1025 \
  -p 8025:8025 \
  mailhog/mailhog

# 配置 kimi 使用测试服务器
# ~/.kimi/config.toml
[inbound_mail.test]
smtp_host = "localhost"
smtp_port = 1025
imap_host = "localhost"  # MailHog 不支持 IMAP，可用 GreenMail 替代
```

### 替代方案：GreenMail（支持 IMAP）

```bash
docker run -d \
  --name greenmail \
  -p 3025:3025 \
  -p 3110:3110 \
  -p 3143:3143 \
  -p 3465:3465 \
  -p 3993:3993 \
  -p 3995:3995 \
  -e GREENMAIL_OPTS="-Dgreenmail.setup.test.all -Dgreenmail.users=test:test@localhost" \
  greenmail/standalone:2.0.0
```

---

## 推荐配置（个人使用）

```toml
[inbound_mail]
enabled = true
security_level = "balanced"  # strict | balanced | trusted

# 只信任自己的邮箱
whitelist = [
    { email = "your-email@gmail.com", dkim_required = true }
]

# 默认行为
default_behavior = {
  auto_execute_readonly = true,    # /review 自动执行
  confirm_write_operations = true, # /code 需要邮件确认
  max_execution_time = "10m",
}

# 快捷指令映射
shortcuts = {
  "fix-bug" = "分析错误原因并修复",
  "add-tests" = "为修改的代码添加单元测试",
  "optimize" = "优化性能并解释改进",
}
```

发送邮件示例：

```
Subject: [AUTO] fix-bug
Body:
附件 test.py 运行报错了，请修复。
```

---

*设计原则: 默认安全，按需开放，全程可审计*
