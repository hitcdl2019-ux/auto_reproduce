# paper-analysis skill

全自动论文解析 skill。接收 GitHub URL、arXiv PDF URL 或本地 PDF 路径，下载并解析论文，提取核心研究信息，生成结构化报告。

## 快速使用

```bash
python ~/.openclaw/skills/paper-analysis/scripts/analyze_paper.py \
  --github-url "https://github.com/zcai0612/UP2You" \
  --paper-url "https://arxiv.org/pdf/2509.24817" \
  --output-root /workspace/.openclaw/workspace
```

## 依赖

- Python 3.8+
- `pymupdf`（脚本会自动安装）
- `wget` 或 Python stdlib `urllib`

## 输出

- 报告：`/workspace/.openclaw/workspace/paper_analysis/<paper_name>/<name>_report.md`
- 原始文本：`/workspace/.openclaw/workspace/paper_analysis/<paper_name>/paper_text.txt`
- JSON 结果（打印到 stdout）
