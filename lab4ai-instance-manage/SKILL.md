---
name: lab4ai-instance-manage
description: Lab4AI 云实例全生命周期管理（创建 + 关闭）。通过 REST API 一站式创建 CPU/GPU 实例并获取 SSH 连接信息，以及按 serverId 关闭释放实例。适用于项目复现流水线中的算力申请与释放环节。
---

# Lab4AI 实例管理 Skill (lab4ai-instance-manage)

通过 Lab4AI 云端 REST API 管理实例的完整生命周期：创建 → 使用 → 释放。

---

## 一、创建实例

**API**: `https://tools.lab4ai.cn/api/v1/tools/instance_create/invoke`

### 命令行

```bash
# 创建 CPU 实例 (2核)
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/create.py "CPU 2核"

# 创建 GPU 实例 (1张)
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/create.py "1张GPU"

# 创建 GPU 实例 (自定义镜像)
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/create.py "GPU 1张 image=my-custom-tag"

# 创建 GPU 实例 (指定项目名)
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/create.py "GPU 1张 name=LightX2V"

# 创建 GPU 实例 (从 GitHub URL 提取项目名)
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/create.py "GPU 1张 https://github.com/ModelTC/LightX2V"
```

### API 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `phone` | string | ✅ | - | 手机号（从 .env 读取） |
| `password` | string | ✅ | - | 密码（从 .env 读取） |
| `targetModel` | string | ✅ | `GPU` | **只接受 `CPU` 或 `GPU`**（不接受 H800A 等具体型号） |
| `cpuCount` | int | ✅ | 2 | CPU 核数 |
| `gpuCount` | int | 否 | - | GPU 卡数（targetModel=GPU 时使用） |
| `imageTag` | string | ✅ | `lf0.9.4-tf4.57.1-torch2.8.0-cu12.6-1.1` | 镜像标签 |
| `source` | string | 否 | `lab` | 来源标识，可选: apps, online, lab, inferne |
| `serverName` | string | 否 | 后端默认 | 实例名称，传入后覆盖后端默认命名 |

### 意图解析规则

| 用户输入关键词 | 解析结果 |
|---|---|
| `CPU`、`核` | targetModel = CPU |
| `H800`、`H800A`、`H100`、`H20`、`GPU`、`显卡`、`训练` | targetModel = GPU |
| 数字 + `张/卡/核` 或独立数字 | 对应资源数量 |
| `image=xxx` | 指定 imageTag |
| `source=xxx` | 指定 source |
| `name=xxx` 或 `project=xxx` | 指定项目名，生成 serverName = `OpenClaw-{项目名}-GPU-{卡数}卡` 或 `OpenClaw-{项目名}-CPU-{核数}C` |
| GitHub URL | 自动提取仓库名作为项目名 |
| 无项目名 | 不传 serverName，后端默认命名 |
| 无数量 | CPU 默认 2 核，GPU 默认 1 张 |

### 创建输出

| 字段 | 说明 |
|---|---|
| `status` | `success` 或 `failed` |
| `serverId` | 实例 ID（用于后续关机） |
| `instanceId` | 实例 UUID |
| `ssh_host` | SSH 主机地址 |
| `ssh_port` | SSH 端口 |
| `ssh_user` | SSH 用户名（固定 root） |
| `ssh_pass` | SSH 密码 |

---

## 二、关闭实例

**API**: `https://tools.lab4ai.cn/api/v1/tools/instance_stop/invoke`

### 命令行

```bash
# 传入 serverId 关闭实例
HOME=/workspace python /workspace/.openclaw/skills/lab4ai-instance-manage/scripts/stop.py <serverId>
```

### 关闭输出

| 字段 | 说明 |
|---|---|
| `status` | `success` 或 `failed` |
| `serverId` | 被关闭的实例 ID |
| `startTime` | 实例开机时间 |
| `stopTime` | 实例关机时间 |

---

## 三、前置条件

- `/workspace/.openclaw/.env` 中配置了 `LAB4AI_PHONE` 和 `LAB4AI_PASSWORD`
- 安装 `httpx`：`pip install httpx`（通常已预装）

## 四、注意事项

1. **targetModel 只接受 `CPU` 或 `GPU`**，H800A/H100 等具体型号由平台自动分配
2. 密码连续错误 5 次会锁定 10 分钟，确保凭证正确
3. 实例创建后需 1~3 分钟 SSHD 才就绪，建议配合 SSH 探活轮询使用
4. 关机操作不可逆，请确认 serverId 正确
5. 刚创建的实例如果还未完全就绪，调用关机可能返回 500，等 30 秒重试即可
