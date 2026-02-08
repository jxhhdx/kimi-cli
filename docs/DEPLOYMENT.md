# 无脑部署

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
```

## 配置环境变量

```bash
export KIMI_EMAIL_ADDRESS="your-email@qq.com"
export KIMI_EMAIL_PASSWORD="你的授权码"
export KIMI_NOTIFY_EMAIL="接收通知的邮箱"
```

## 测试

```bash
kimi2 mail test
kimi2 --print -y -p "Hello"
```

---

**完成！** 🎉
