# paper-analysis 技术笔记

## PyMuPDF 常见问题

### 导入错误
```
ModuleNotFoundError: No module named 'fitz'
```
解决：
```bash
pip install pymupdf
```

### libstdc++ 版本问题（Linux / Nix）
某些 Nix 环境会遇到 GLIBC 版本不兼容：
```bash
# 如果遇到 libstdc++.so.6 报错，考虑用 conda 版本的 pymupdf
conda install -c conda-forge pymupdf
```

## PDF 下载注意

### User-Agent
arXiv 等站点对 Python 默认 UA 有限制，wget/urllib 需要设置：
```python
headers={"User-Agent": "Mozilla/5.0"}
```

### arXiv PDF URL 格式
```
https://arxiv.org/pdf/<arXiv_ID>.pdf
# 例: https://arxiv.org/pdf/2509.24817.pdf
```

### 从 GitHub README 解析 arXiv 链接
常见正则模式：
```python
r"https://arxiv\.org/abs/([0-9\.]+)"
r"https://arxiv\.org/pdf/([0-9\.]+)"
r"arxiv\.org/abs/([0-9\.]+)"
r"[![arXiv]].*?([0-9]{4}\.[0-9]{4,})"
```

## 数值表格提取策略

当前脚本采用**简化行级提取**（split by newline），适合格式规范的论文表格。

对于复杂表格（如跨列、合并单元格），建议后续升级为：
- `tabula-py` — Java 依赖，表格识别准确
- `camelot` — PDF 表格提取
- `MinerU skill` — 更 robust 的解析方案

## arXiv ID 版本号处理

arXiv 论文可能有多个版本（v1, v2, ...），URL 中的版本号决定具体版本：
- `2509.24817` — 指向最新版本
- `2509.24817v1` — 指向 v1

建议统一使用不带版本号的 ID，arXiv 会自动重定向到最新版本。
