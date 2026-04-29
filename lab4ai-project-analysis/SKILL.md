---
name: lab4ai-project-analysis
description: 项目审计与可行性评估工具。通过静态扫描和干跑测试，快速评估 GitHub 项目的难度，提前发现依赖冲突、死链、硬编码路径、Gated Model 等问题。
---

# Repo Auditor Skill

项目复现可行性分析工具，帮助你在投入大量时间之前快速评估一个 GitHub 项目是否值得复现。

## 核心理念

**"干跑（Dry-Run）与静态扫描"** - 不需要真的租 GPU、配环境、跑训练，通过快速审查项目结构，提前判断这个项目是不是个“坑”。

## 功能特性

### 1. 依赖冲突检测
- 解析 requirements.txt / environment.yml / setup.py
- 使用 pip dry-run 检测依赖冲突
- 识别过时或废弃的包版本

### 2. 数据集死链探测
- 提取 README 和代码中的所有外部链接
- 测试 Google Drive、百度网盘、Dropbox、HuggingFace 等链接的连通性
- 检测需要私有访问权限的资源

### 3. 硬编码路径扫描
- 全局扫描 .py 和 .sh 文件
- 识别绝对路径（如 /home/username/data/）
- 标记 Windows 风格路径（C:\Users\...）

### 4. README 完整性解析
- 检查是否有数据预处理指令
- 检查是否有训练指令
- 检查是否有评估指令
- 利用大模型评估文档完整性

### 5. Gated Model 扫描 🆕
- 扫描代码中所有 `from_pretrained("org/model")` 调用
- 通过 HuggingFace API 检测模型是否为 gated/restricted
- 查询本地镜像映射表 (`gated_model_mirrors.yaml`) 提供替代下载源
- 避免在 GPU 推理阶段才发现模型下载失败

## 使用方法

```bash
python ~/.openclaw/skills/repo-auditor/scripts/main.py <GitHub仓库URL>
```

## 输出报告

- 复现可行性打分(0-100分)
- 环境解析结果
- 数据链状态
- 代码坏味道
- 复现建议

### 报告保存位置

项目可行性分析报告会自动保存到以下目录:
```
/workspace/.openclaw/workspace/{{repo_name}}/{{repo_name}}_Audit_Report.md
```

其中 `<repo_name>` 为 GitHub 仓库名称(如 `nanoGPT`)。
