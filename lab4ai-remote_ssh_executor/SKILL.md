---
name: lab4ai-remote_ssh_executor
description: "跨平台远程 SSH 执行器（自带防弹探活机制）"
---

# 🚀 跨平台远程 SSH 执行器 (Lab4AI Remote SSH)

## 🤖 技能定位与红线纪律
你是替代传统 `claw-shell` + `sshpass` 的**终极远程命令执行工具**。由于宿主机可能是 Windows，你**绝对禁止**尝试在本地生成 `ssh` 进程。所有针对远程 Linux 服务器的操作，必须调用本技能！

## ⚡ 核心特性
本底层 Python 脚本已经内置了长达 **5分钟（30次）的 SSH 探活循环**。
**🚨 严禁画蛇添足：**
你在传递 `command` 参数时，直接写业务代码即可！**绝对禁止**在 `command` 里编写 `while ! ssh... do sleep 10` 等探测逻辑，底层会替你搞定一切连接等待！

## 💡 调用示例 (JSON 结构参考)
```json
{
  "host": "123.45.67.89",
  "port": 22022,
  "username": "root",
  "password": "your_secure_password",
  "command": "export http_proxy=http://10.201.85.65:1080 && export https_proxy=http://10.201.85.65:1080\nmkdir -p /workspace/data\ncd /workspace/data\ngit clone https://github.com/xxx/xxx.git"
}