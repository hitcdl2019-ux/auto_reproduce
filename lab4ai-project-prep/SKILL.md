---
name: lab4ai-project-prep
description: 在远程 Lab4AI 实例上全自动执行项目准备工作（Conda 环境创建、依赖安装、数据下载、权重下载）。通过 SSH 将组装好的 Bash 脚本送入远程执行，自动处理代理、环境变量、Conda 复用检测、依赖安装重试和无状态 SSH 闭环。适用于复现流水线 Step 4，在廉价 CPU 实例上完成耗时的下载和纯 Python 依赖安装。
---

# Remote Project Prep Skill

在远程 Lab4AI 实例上一站式完成项目复现的前置准备工作。

## 职责边界

**本 skill 负责"执行"**：Conda 环境创建、依赖安装、数据下载、权重下载。
**Step 4 YAML 负责"决策"**：SSH 探活、git clone、分析审计报告、组装命令数组。

两者不重叠。Agent 不要自己创建 Conda 环境或安装依赖，全部交给本 skill。

## 工作原理

0. **系统基础开发库预装**（GL/X11/编译工具一次性装齐）+ **CMake 版本检测**（低于 3.28 自动升级）
1. **检测 Conda 环境是否已存在**（存在则跳过创建，避免重复）
1b. **大象库检测与预编译替代**（扫描 vcpkg.json，VTK/OpenCV/Boost 等大库走 apt，小库继续走 vcpkg）
1c. **CUDA 特性剥离**（CPU 实例无 GPU，剥离 vcpkg 依赖中的 cuda 特性，记录到 `cuda_features.json` 供 GPU 阶段恢复）
2. 根据传入的 `python_version` 创建隔离 Conda 环境
3. 按顺序执行 `dependency_cmds`（每条命令失败自动重试 2 次）
4. 按顺序执行 `data_cmds`
5. 按顺序执行 `weight_cmds`（每条命令失败自动重试 2 次）
6. 超时 2 小时自动终止

## 前置条件

- 远程实例已启动且 SSHD 已就绪（step_4 负责探活）
- 本机已安装 `sshpass`
- 远程实例已创建好目录结构并 git clone 代码到 `/workspace/user-data/codelab/{{repo_name}}/code/`（step_4 负责）

## 目录结构

```
/workspace/user-data/codelab/{repo_name}/
├── code/          ← GitHub 代码（git clone 到此）
│   ├── <源码文件>
│   ├── data -> ../dataset      ← 软链接（若项目代码引用 ./data）
│   ├── dataset -> ../dataset   ← 软链接（若项目代码引用 ./dataset）
│   ├── model -> ../model       ← 软链接（若项目代码引用 ./model）
│   └── <项目硬编码路径> -> ../dataset 或 ../model  ← 按需动态创建
├── dataset/       ← 数据集存放
├── model/         ← 模型权重存放
└── README.md      ← 复现说明
```

**硬性规定**：项目根目录下只允许存在 `code/`、`dataset/`、`model/` 三个文件夹和一个 `README.md`。
所有运行产物、符号链接、输出目录必须放在 `code/` 内部。

Skill 执行时会：
1. 确认 `dataset/` 和 `model/` 目录存在
2. 在 `code/` 内部创建 `data -> ../dataset`、`dataset -> ../dataset` 和 `model -> ../model` 软链接
3. 自动扫描项目配置文件中硬编码的相对路径（如 `../dataset`、`../checkpoints`），在 `code/` 内部创建对应软链接指向 `../dataset` 或 `../model`
4. 最终清理：确保项目根目录下不存在 `code/`、`dataset/`、`model/`、`README.md` 以外的任何文件或目录

## 入参

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `ssh_ip` | string | ✅ | - | 远程实例 IP（来自 step_3 的 `ssh_host`） |
| `ssh_port` | string | ✅ | - | SSH 端口（来自 step_3 的 `ssh_port`） |
| `ssh_password` | string | ✅ | - | SSH 密码（来自 step_3 的 `ssh_pass`） |
| `repo_name` | string | ✅ | - | 项目名称（如 `UP2You`） |
| `python_version` | string | 否 | `3.10` | Python 版本，由 Agent 从审计报告中提取 |
| `dependency_cmds` | string[] | ✅ | - | 依赖安装命令列表（含 PyTorch 底座） |
| `data_cmds` | string[] | 否 | `[]` | 数据下载/预处理命令列表 |
| `weight_cmds` | string[] | 否 | `[]` | 模型权重下载命令列表 |
| `vcpkg_json_path` | string | 否 | `None` | 远程实例上 vcpkg.json 的绝对路径，传入后启用大象库检测和 CUDA 特性剥离 |
| `enable_elephant_detect` | bool | 否 | `True` | 是否启用大象库检测（需同时传入 vcpkg_json_path） |

## 使用示例

```python
from prep_runner import run_remote_prep

result = run_remote_prep(
    ssh_ip="182.242.159.112",
    ssh_port="31264",
    ssh_password="9KlprdQnGS",
    repo_name="UP2You",
    python_version="3.10",
    dependency_cmds=[
        "pip install torch==2.4.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118",
        "pip install -r requirements.txt"
    ],
    weight_cmds=[
        "huggingface-cli download zcai0612/UP2You --local-dir pretrained_models"
    ]
)
```

## 远程脚本执行阶段

```
[0/6] 系统基础开发库预装 + CMake 版本检测升级
      → apt-get install GL/X11/编译工具全套，10-20 秒完成
      → CMake < 3.28 时自动 pip install cmake 升级
[1/6] 检测并创建 Conda 环境
      → 已存在则跳过，否则 conda create python={{python_version}}
[2/6] 大象库检测与预编译替代
      → 扫描 vcpkg.json，命中 VTK/OpenCV/Boost 等大库走 apt 秒装
      → 从 vcpkg.json 中移除已替代的库，避免 vcpkg 源码编译
[3/6] CUDA 特性剥离
      → 检测 vcpkg.json 中带 cuda 特性的依赖，临时移除
      → 生成 cuda_features.json 记录剥离信息，供 GPU 阶段恢复
      → 设置 VCPKG_MAX_CONCURRENCY=$(nproc) + VCPKG_BUILD_TYPE=release
[4/6] 安装依赖
      → 按顺序执行 dependency_cmds，每条失败重试 2 次
[5/6] 下载数据
      → 按顺序执行 data_cmds（如有）
[6/6] 下载权重
      → 按顺序执行 weight_cmds，每条失败重试 2 次（如有）
```

## 自动注入的环境变量

```bash
export http_proxy=http://10.201.85.65:1080
export https_proxy=http://10.201.85.65:1080
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
```

## 输出

| 状态 | 返回内容 |
|---|---|
| 成功 | `✅ 远程项目准备全部成功！` + 最后 2000 字符日志 |
| 失败 | `❌ 远程执行报错 (Exit Code X)` + 完整错误日志 |
| 超时 | `❌ 执行超时（超 2 小时）` |
| 连接异常 | `❌ 系统级连接错误: ...` |

## 重试机制

- `dependency_cmds` 和 `weight_cmds` 中的每条命令失败后自动重试 2 次（间隔 5/10 秒）
- `data_cmds` 不重试（数据脚本通常有自己的断点续传逻辑）
- 脚本使用 `set -e`，任何命令（含重试后）最终失败会立即终止

## 注意事项

1. **Conda 环境路径**固定为 `/workspace/envs/{{repo_name}}`，在共享存储上，GPU 实例可直接复用
2. **本 skill 不含 SSH 探活逻辑**，需由 step_4 的阶段 A 保证连通性
3. **本 skill 不做 git clone**，需由 step_4 的阶段 A 完成
4. **超时 2 小时**，超大数据集可能不够
5. **强制 root 用户**
6. **大象库检测**需传入 `vcpkg_json_path` 才会启用，纯 Python 项目无需传入
7. **CUDA 特性剥离记录** `cuda_features.json` 保存在 vcpkg.json 同级目录，Step 7 GPU 阶段需读取并恢复
8. **vcpkg 优化参数**（CONCURRENCY/BUILD_TYPE）仅在传入 vcpkg_json_path 时设置
