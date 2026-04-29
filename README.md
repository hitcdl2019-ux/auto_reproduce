# Lab4AI Skills — 全自动论文/项目复现工具集

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Lab4AI-brightgreen.svg)](https://lab4ai.cn)
[![Agent](https://img.shields.io/badge/agent-OpenClaw-orange.svg)](https://openclaw.ai)

**源码仓库（Codeup）：** [lab4ai-skills](https://codeup.aliyun.com/6864d2567151135f7b9b3601/LLaMaFactory-online/LLMclass/lab4ai-skills.git)

> 一套面向 AI Agent 的自动化技能包，覆盖 **项目审计 → 论文解析 → 算力调度 → 环境构建 → 推理/训练 → 报告生成** 的端到端论文复现全流程。

## ✨ 核心特性

- 🔍 **智能项目审计** — 自动扫描 GitHub 仓库，评估复现可行性（依赖、环境、风险项）
- 📄 **论文深度解析** — 提取 Baseline 指标、超参数、创新点，生成结构化报告
- 🖥️ **算力自动调度** — 一键创建/释放 Lab4AI CPU/GPU 实例，杜绝算力空转
- 🐘 **大象库智能检测** — VTK、OpenCV、Boost 等大型 C++ 库自动走 apt 预编译，避免源码编译耗时爆炸
- 🔧 **CUDA 特性智能剥离/恢复** — CPU 阶段自动剥离 CUDA 特性加速构建，GPU 阶段自动恢复
- 📊 **工业级报告生成** — 自动排版 Word 文档，含指标对比表、排坑记录、超参数档案

## 📦 技能清单

| Skill | 说明 | 对应流水线阶段 |
|-------|------|--------------|
| [lab4ai-project-analysis](./lab4ai-project-analysis/) | 项目复现可行性分析，输出评分和风险项 | Step 1 |
| [lab4ai-paper-analysis](./lab4ai-paper-analysis/) | 论文 PDF 解析，提取指标和超参数 | Step 1 |
| [lab4ai-instance-manage](./lab4ai-instance-manage/) | Lab4AI 实例创建与释放（CPU/GPU） | Step 3/5/6/9 |
| [lab4ai-project-prep](./lab4ai-project-prep/) | 远程环境准备（系统库预装/大象库替代/Conda/依赖/数据/权重） | Step 4 |
| [lab4ai-auto-reproduct](./lab4ai-auto-reproduct/) | **复现流水线主控**，编排所有 skill 的 9 步工作流 | 全流程 |
| [lab4ai-repro-report](./lab4ai-repro-report/) | 生成 Word 格式复现报告 | Step 8 |

## 🚀 快速开始

### 前置条件

- [OpenClaw](https://openclaw.ai) Agent 环境
- Lab4AI 平台账号（用于算力调度）
- 认证凭证配置在 `/root/.openclaw/.env`

### 环境变量配置

在 `/root/.openclaw/.env` 中配置 Lab4AI 平台登录凭证（**必填**）：

```bash
# /root/.openclaw/.env

# Lab4AI 平台注册手机号（必填）
LAB4AI_PHONE=138xxxxxxxx

# Lab4AI 平台登录密码（必填）
LAB4AI_PASSWORD=your_password_here
```

> ⚠️ **安全提示**：`.env` 文件包含敏感凭证，请勿提交到 Git 仓库。流水线中的实例创建和释放（Step 3/5/6/9）均依赖此配置自动登录平台获取 Token。

### 安装

```bash
# 克隆仓库
git clone https://codeup.aliyun.com/6864d2567151135f7b9b3601/LLaMaFactory-online/LLMclass/lab4ai-skills.git

# 将 skill 目录复制到 OpenClaw skills 目录
cp -r lab4ai-skills/lab4ai-* ~/.openclaw/skills/

# 安装 vendor 依赖（将 claw-shell、file-system、ssh-essentials 软链接到 skills 目录）
bash ~/.openclaw/skills/lab4ai-auto-reproduct/install.sh
```

### 使用方式

对 Agent 说：

```
复现这个项目 https://github.com/
```

或附带论文链接：

```
复现这个项目 https://github.com/
论文地址：https://arxiv.org/pdf/xxxx.xxxxx
```

Agent 会自动启动 9 步复现流水线。

## 📋 复现流水线全流程

```
┌─────────────────────────────────────────────────────┐
│  Step 1  项目审计 + 论文解析                          │
│          → 可行性评分、Baseline 指标、超参数提取        │
├─────────────────────────────────────────────────────┤
│  Step 2  复现可行性熔断判断                            │
│          → score < 60 自动终止，≥ 60 继续              │
├─────────────────────────────────────────────────────┤
│  Step 3  创建 CPU 实例（廉价算力做脏活）                │
├─────────────────────────────────────────────────────┤
│  Step 4  CPU 环境准备                                 │
│          → SSH 探活 + git clone                       │
│          → 系统基础库预装（GL/X11/编译工具）             │
│          → CMake 版本检测升级                          │
│          → 大象库检测（VTK/OpenCV 等走 apt 秒装）       │
│          → CUDA 特性剥离（CPU 无 GPU，记录供恢复）       │
│          → Conda 环境 + 依赖安装 + 数据/权重下载         │
├─────────────────────────────────────────────────────┤
│  Step 5  释放 CPU 实例                                │
├─────────────────────────────────────────────────────┤
│  Step 6  创建 GPU 实例（H100/H800A）                   │
├─────────────────────────────────────────────────────┤
│  Step 7  GPU 执行                                     │
│          → CUDA 特性恢复 + 系统库预装                   │
│          → CUDA 扩展编译（自愈排障）                     │
│          → Smoke Test 推理/训练                        │
│          → 指标抓取 + Baseline 对比                     │
│          → 环境补丁记录（env_patches.md）               │
├─────────────────────────────────────────────────────┤
│  Step 8  生成 Word 复现报告                            │
├─────────────────────────────────────────────────────┤
│  Step 9  释放 GPU 实例                                │
└─────────────────────────────────────────────────────┘
```

## 📁 项目代码、数据与模型目录规范

复现流水线在 Lab4AI 实例上严格遵循以下目录结构，代码、数据、模型权重**三者分离**：

```
/workspace/user-data/codelab/{repo_name}/
│
├── code/                          ← GitHub 代码（git clone 到此）
│   ├── requirements.txt
│   ├── CMakeLists.txt             ← C++ 项目构建文件（如有）
│   ├── vcpkg.json                 ← vcpkg 依赖声明（如有）
│   ├── cuda_features.json         ← [自动生成] CUDA 特性剥离记录
│   ├── data -> ../data            ← 软链接，项目代码可直接引用 ./data/
│   └── model -> ../model          ← 软链接，项目代码可直接引用 ./model/
│
├── data/                          ← 数据集存放（Step 4 下载）
│   ├── train/
│   ├── val/
│   └── ...
│
├── model/                         ← 模型权重存放（Step 4 下载）
│   ├── pretrained_models/
│   └── ...
│
├── env_patches.md                 ← [自动生成] 环境补丁记录（Step 7）
└── repro_run.log                  ← [自动生成] 推理/训练运行日志（Step 7）
```

**Conda 环境路径：**

```
/workspace/envs/{repo_name}/       ← 隔离的 Conda 虚拟环境（CPU/GPU 实例共享存储，无需重建）
```

### 路径设计说明

| 目录/文件 | 路径 | 说明 |
|----------|------|------|
| 项目代码 | `/workspace/user-data/codelab/{repo_name}/code/` | git clone 目标目录 |
| 数据集 | `/workspace/user-data/codelab/{repo_name}/data/` | 所有数据下载到此 |
| 模型权重 | `/workspace/user-data/codelab/{repo_name}/model/` | 所有权重下载到此 |
| 软链接 data | `code/data -> ../data` | 项目代码中 `./data/` 路径无需修改 |
| 软链接 model | `code/model -> ../model` | 项目代码中 `./model/` 路径无需修改 |
| Conda 环境 | `/workspace/envs/{repo_name}/` | CPU/GPU 实例共享，创建一次复用 |
| CUDA 特性记录 | `code/cuda_features.json` | CPU 阶段自动生成，GPU 阶段读取恢复 |
| 环境补丁记录 | `env_patches.md` | Step 7 自动生成，记录构建系统修改 |
| 运行日志 | `repro_run.log` | Step 7 推理/训练的完整终端日志 |

## 📤 输出文档

流水线执行完毕后，自动产出以下文档：

| 输出文件 | 路径 | 生成阶段 | 说明 |
|---------|------|---------|------|
| 综合审计报告 | `/root/.openclaw/workspace/{repo_name}/{repo_name}_Audit_Report.md` | Step 1 | 项目可行性分析 + 论文 Baseline 指标 + 超参数，Markdown 格式 |
| 论文解析产物 | `/root/.openclaw/workspace/paper_analysis/paper_analysis/{repo_name}/` | Step 1 | 论文 PDF 原文、提取文本、结构化报告（中间参考文件） |
| CUDA 特性记录 | `/workspace/user-data/codelab/{repo_name}/code/cuda_features.json` | Step 4 | CPU 阶段剥离的 CUDA 特性，JSON 格式，供 GPU 阶段恢复 |
| 环境补丁记录 | `/workspace/user-data/codelab/{repo_name}/env_patches.md` | Step 7 | 对构建系统的所有修改（CMakeLists.txt、vcpkg.json、系统库等） |
| 运行日志 | `/workspace/user-data/codelab/{repo_name}/code/repro_run.log` | Step 7 | 推理/训练完整终端日志 |
| **复现报告（终极交付物）** | `/root/.openclaw/workspace/{repo_name}/{repo_name}_Final_Repro_Report.docx` | **Step 8** | **工业级 Word 文档**，含项目档案、指标对比、排坑记录、超参数、优化建议 |

## 📊 复现案例

以下是已经通过本工具集完成端到端复现的真实项目：

| # | 项目名 | GitHub | 论文 | 项目类型 | 评分 | 复现结果 |
|---|--------|--------|------|------|------|--------|
| 1 | **nanoGPT** | [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) | — | LLM 训练 | 80/100 | ✅ 复现成功，全流程跑通 |
| 2 | **UP2You** | [zcai0612/UP2You](https://github.com/zcai0612/UP2You) | [arXiv:2509.24817](https://arxiv.org/abs/2509.24817) | 3D 人像重建，纯推理 | 68/100 | ✅ 复现成功，H100 推理 5 分钟，输出 3D 模型 |
| 3 | **HypModalAlign** | [MCISLAB/HypModalAlign](https://github.com/MCISLAB-Manifold-Learning/HypModalAlign) | [arXiv:2510.27391](https://arxiv.org/abs/2510.27391) | 跨模态层次化对齐，训练类 | 75/100 | ✅ 复现成功，Smoke Test 训练方向正确 |
| 4 | **A2MADA-YOLO** | [HaoxingZhou/A2MADA-YOLO](https://github.com/HaoxingZhou/A2MADA-YOLO) | — | 域适应目标检测，训练类 | 60/100 | ✅ 复现成功，标准 YOLOv7 训练跑通 |
| 5 | **FreeFlow** | [changyu-hu/FreeFlow](https://github.com/changyu-hu/FreeFlow) | NeurIPS 2025 | 流固耦合仿真，C++/CUDA | 72/100 | ✅ 编译成功（催生了大象库检测等优化） |
| 6 | **VLM-RMD-release** | [VLM-RMD/VLM-RMD-release](https://github.com/VLM-RMD/VLM-RMD-release) | [arXiv:2503.18349](https://arxiv.org/abs/2503.18349) | 人-物交互策略，ICLR 2026 | **8/100** | ❌ 熔断终止（仓库无可执行代码） |

> 💡 案例 6 展示了熔断机制的实际效果：论文质量 78 分但代码仅 8 分，流水线在 Step 2 自动终止，避免浪费算力。

## 🐘 大象库智能检测

当项目依赖 VTK、OpenCV、Boost 等大型 C++ 库时，vcpkg 源码编译可能耗时数十分钟甚至数小时。本工具集会自动：

1. **扫描** `vcpkg.json` 中的依赖
2. **识别**大象库（VTK → `libvtk9-dev`、OpenCV → `libopencv-dev` 等）
3. **替换**为 apt 预编译包（10 秒搞定）
4. **移除** vcpkg.json 中对应条目，避免重复编译

当前支持的大象库：

| 库名 | apt 替代包 |
|------|-----------|
| VTK | `libvtk9-dev` |
| OpenCV | `libopencv-dev` |
| Boost | `libboost-all-dev` |
| CGAL | `libcgal-dev` |
| PCL | `libpcl-dev` |
| ITK | `libinsighttoolkit5-dev` |

## 🔧 CUDA 特性智能剥离/恢复

针对 CPU 与 GPU 分阶段执行的场景：

- **CPU 阶段（Step 4）**：自动检测 vcpkg 依赖中的 `cuda` 特性并剥离，生成 `cuda_features.json` 记录
- **GPU 阶段（Step 7）**：读取记录文件，恢复 CUDA 特性，重新编译 CUDA 相关包

同时自动设置 vcpkg 优化参数：
- `VCPKG_MAX_CONCURRENCY=$(nproc)` — 匹配实际 CPU 核数
- `VCPKG_BUILD_TYPE=release` — 跳过 Debug 编译，节省一半时间

## 🛡️ 安全机制

- **资源保底释放**：任何步骤失败时，自动释放已申请的算力实例，杜绝空转烧钱
- **熔断机制**：可行性评分低于 60 分自动终止，不浪费算力
- **重试机制**：依赖安装和权重下载自动重试 2 次
- **超时保护**：环境准备阶段 2 小时超时自动终止

## 📁 Skill 源码目录结构

```
lab4ai-skills/
├── README.md
├── program.md                       # （可选）入口跳转，完整内容见 lab4ai-auto-research/
├── lab4ai-auto-research/            # 自动化训练实验管线（pipeline.yml + skill_01…08）
│   ├── SKILL.md
│   ├── pipeline.yml
│   └── scripts/
│       ├── skill_01lab_instance.md … skill_08stop_instance.md
│       └── create_env.md
├── lab4ai-auto-reproduct/           # 复现流水线主控
│   ├── SKILL.md                     # 技能说明与执行纪律
│   ├── project_reproduce.yaml       # 9 步工作流定义（核心编排文件）
│   ├── install.sh                   # 依赖安装脚本
│   └── vendor/                      # 内置依赖 skill
│       ├── claw-shell/              # Shell 命令执行
│       ├── file-system/             # 文件读写
│       └── ssh-essentials/          # SSH 连接
├── lab4ai-project-analysis/         # 项目可行性分析
│   ├── SKILL.md
│   └── scripts/main.py
├── lab4ai-paper-analysis/           # 论文解析
│   ├── SKILL.md
│   ├── skill.json
│   ├── scripts/analyze_paper.py
│   └── references/notes.md
├── lab4ai-instance-manage/          # 实例生命周期管理
│   ├── SKILL.md
│   └── scripts/
│       ├── create.py                # 创建实例
│       └── stop.py                  # 关闭实例
├── lab4ai-project-prep/             # 远程环境准备
│   ├── SKILL.md
│   ├── manifest.yaml
│   └── prep_runner.py               # 核心执行逻辑（含大象库检测/CUDA剥离）
└── lab4ai-repro-report/             # 报告生成
    ├── SKILL.md
    ├── manifest.yaml
    └── report_generator.py           # Word 文档生成引擎
```

## 🔄 更新日志

### v1.1.0 (2026-04-11)

- **lab4ai-project-prep**：新增系统基础库预装、大象库智能检测、CUDA 特性剥离、CMake 版本升级
- **lab4ai-auto-reproduct**：Step 4 新增构建类型识别与 `vcpkg_json_path` 传参；Step 7 新增 CUDA 特性恢复和环境补丁记录
- 新增 README 项目文档

### v1.0.0 (2026-04-08)

- 初始版本，完成 UP2You 项目端到端复现验证

## 📄 License

MIT
