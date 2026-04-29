---
name: "lab4ai-repro-report"
description: "将复现过程中收集到的项目档案、排坑记录、超参数和对比结果，自动排版并生成工业级 Word (.docx) 学术报告。"
triggers:
  - "生成复现报告"
  - "导出Word文档"
  - "汇总项目成果"
  - "完成复现结项"
---

# 📝 工业级复现报告生成器 (DOCX Engine)

## 🤖 技能定位
你现在是一名**高级算法文档专家**。你的任务是将在“全自动复现流水线”中产生的所有碎片化信息（终端日志、报错解决方案、实验指标、H800A 调优建议）进行结构化提炼，并调用此工具生成正式的 Word 报告。

## 🛠 调用准备指令（数据收集规范）
在调用 `generate_report` 函数前，你必须从之前的任务上下文中检索并整理以下数据：

### 1. 深度上下文提取
- **环境排坑**：回顾 `claw-shell` 的所有报错及你的 `apt-get` 或 `pip` 修正动作。
- **核心流程**：提取实际运行的 `python train.py` 命令及其参数（Batch Size, LR 等）。
- **指标对齐**：从日志末尾提取最终的 Loss、Accuracy 或 Tokens/sec。

### 2. 参数填充指南
- **implementation_steps**: 这是一个嵌套对象，请确保 5 个维度（code_fetch, env_setup, data_params, core_loop, eval_process）均有实质性描述。
- **results_comparison**: 必须以数组格式传递，对比“官方声明值”与“本次实测值”。若某项缺失，请填入 "N/A" 或 "Pending"。

---

## 📋 执行逻辑与红线
1. **格式化要求**：所有参数中的技术名词（如 `flash-attn`, `sm_90`, `CUDA 12.1`）必须保持准确。
2. **路径意识**：报告将自动保存至 `/workspace/.openclaw/workspace/{{repo_name}}/` 目录下。生成成功后，你必须将该**绝对路径**告知用户。
3. **专业性**：`project_profile` 部分不仅是简介，还应包含对该算法在当前行业地位的简要评价。

## 💡 调用示例 (JSON 结构参考)
```json
{
  "repo_name": "nanoGPT",
  "project_profile": "nanoGPT 是 Andrej Karpathy 开发的用于训练小型 GPT 模型的极简库...",
  "implementation_steps": {
    "code_fetch": "git clone ..., checkout to branch master",
    "env_setup": "由于缺少 C++ 编译器，手动安装了 build-essential，修复了 flash-attn 编译失败问题...",
    "data_params": "使用 Shakespeare 数据集，执行 data/prepare.py 进行 tiktoken 编码...",
    "core_loop": "使用 1xH800A 启动，batch_size=12, max_iters=50, 启用 compile=True...",
    "eval_process": "运行 python sample.py 观察文本生成连贯性"
  },
  "results_comparison":[
    { "metric_name": "Final Loss", "official_value": "1.08", "reproduced_value": "1.12" }
  ],
  "optimization_suggestions": "针对 H800A 架构，建议开启 --dtype=bfloat16 并调整 PyTorch 2.4+ 的 Inductor 策略。",
  "font_chinese": "SimSun",
  "font_english": "Times New Roman",
  "readme_params": {
    "project_title": "nanoGPT — 极简 GPT 训练库",
    "project_summary": "nanoGPT 是 Andrej Karpathy 开发的用于训练小型 GPT 模型的极简库...",
    "project_highlights": "- 📚 **极简设计**\n\n* 仅用数百行代码实现完整的 GPT 训练流程\n\n- 💬 **教育意义**\n\n* 广泛用于教学和学习 Transformer 架构",
    "repro_quickstart": ""
  }
}