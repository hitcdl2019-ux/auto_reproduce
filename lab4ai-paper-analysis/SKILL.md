---
name: lab4ai-paper-analysis
description: 全自动论文解析工具。接收 GitHub URL 或 PDF URL / 本地路径，自动下载论文 PDF，利用 PyMuPDF 提取全文，通过结构化搜索提取核心信息，生成结构化报告。
---

# Paper Analysis Skill

全自动论文解析 skill。接收 GitHub 项目链接、arXiv PDF URL 或本地 PDF 路径，下载并解析论文，提取核心研究信息，生成结构化报告保存至工作区。

## 核心能力

- **自动下载**：从 arXiv DOI / PDF URL / GitHub 间接引用下载论文 PDF
- **全文解析**：PyMuPDF 快速提取文本，支持超长论文（50+ 页）
- **结构化提取**：
  - 研究背景与核心创新点（从 Abstract / Introduction 提炼）
  - 实验数据集与评测指标
  - 官方 Baseline 指标数值（论文中 Table 数据）
  - 训练超参数（若有）
  - 关键架构参数
- **报告生成**：Markdown 格式，默认写入 `{output_root}/{paper_name}/{paper_name}_report.md`（可通过 `--output-dir` 覆盖）
- **上下文记忆**：将核心指标写入 MEMORY.md，供后续 agent steps 使用

## 输入

| 参数 | 类型 | 说明 |
|------|------|------|
| `github_url` | string | GitHub 项目 URL（自动从 README 提取论文链接） |
| `paper_url` | string | arXiv PDF URL 或本地路径（可选） |
| `paper_path` | string | 本地 PDF 绝对路径（可选，覆盖 URL） |

> 优先顺序：`paper_path` > `paper_url` > `github_url`（从 README 解析）

## 使用方法

### 方式一：作为 agent skill 自动触发
当用户说"分析论文""解析 paper""提取论文指标"等时自动激活。

### 方式二：直接调用脚本
```bash
python ~/.openclaw/skills/paper-analysis/scripts/analyze_paper.py \
  --github-url "https://github.com/xxx/yyy" \
  --paper-url "https://arxiv.org/pdf/xxxx.xxxxx" \
  --output-root /workspace/.openclaw/workspace
```

### 方式三：Python 模块调用
```python
from paper_analysis import analyze_paper

result = analyze_paper(
    github_url="https://github.com/xxx/yyy",
    paper_url="https://arxiv.org/pdf/xxxx.xxxxx",
    output_root="/workspace/.openclaw/workspace"
)
print(result["score"])      # 论文质量评分
print(result["metrics"])    # 核心指标字典
print(result["hyperparams"]) # 超参数字典
print(result["report_path"]) # 报告文件路径
```

## 分析流程

```
1. 输入解析
   ├── paper_path → 直接使用本地 PDF
   ├── paper_url  → wget 下载
   └── github_url → 抓取 README，解析 arXiv 链接，再下载 PDF

2. PDF 下载（如需）
   └── wget -q -O <tmp>/paper.pdf <url>

3. PDF 文本提取
   ├── PyMuPDF fitz.open() 按页提取
   ├── 保存为 paper_text.txt（完整原始文本）
   └── 计算页数 / 总字符数

4. 结构化信息提取（Python 字符串搜索）
   ├── Abstract      → 背景 / 创新点 / 主要贡献
   ├── Introduction  → 研究问题定义
   ├── Experiments   → 数据集 / 指标 / 对比方法
   ├── Tables (1-8)  → 数值型 baseline 指标
   ├── Training / D.x → 训练超参数（若适用）
   └── Conclusion    → 总结

5. 报告生成
   └── Markdown 格式，写入 {output_root}/{paper_name}/ 或 --output-dir 指定的目录

6. 上下文记忆
   ├── 更新 MEMORY.md（核心指标 + 超参数）
   └── 供下游 Step 7/8 使用
```

## 输出结构

### 返回值（Python 函数）
```python
{
    "paper_name": str,       # 论文简称
    "arxiv_id": str,         # arXiv ID
    "venue": str,            # 发表 venue (NeurIPS, ICLR, etc.)
    "score": float,          # 综合评分 (0-100)，基于方法创新+实验完整性
    "metrics": {
        "main_baseline": {...},   # 主对比表格数据
        "shape_metrics": {...},   # 形状预测指标（如有）
        "ablation": {...},        # 消融实验数据
    },
    "hyperparams": {
        "batch_size": int,
        "learning_rate": float,
        "epochs": int,
        "additional": {...}
    },
    "datasets": [str, ...],
    "innovation_points": [str, ...],
    "report_path": str,
}
```

### Markdown 报告结构
```markdown
# <Paper Title>

## 基本信息
arXiv ID / Venue / Authors

## 研究背景与创新点

## 实验设置
### 数据集
### 评测指标

## 核心 Baseline 指标（官方发布）

## 训练超参数（如适用）

## 关键架构参数
```

## 技术栈

- **wget** — PDF 下载
- **PyMuPDF (fitz)** — PDF 文本提取
- **Python stdlib** — 字符串搜索 / 正则提取
- **re (re)** — 数值表格解析（备选）
