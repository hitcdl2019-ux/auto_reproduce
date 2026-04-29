#!/usr/bin/env python3
"""
paper_analysis.py —全自动论文解析脚本
接收 github_url / paper_url / paper_path，自动下载+解析+生成报告
"""

import argparse
import os
import re
import sys
import json
import subprocess
import urllib.request
from pathlib import Path

DEFAULT_OUTPUT_ROOT = "/workspace/.openclaw/workspace"
os.environ["http_proxy"] = "http://10.201.85.65:1080"
os.environ["https_proxy"] = "http://10.201.85.65:1080"


def ensure_deps():
    """确保 PyMuPDF 已安装"""
    try:
        import fitz
    except ImportError:
        print("[paper-analysis] PyMuPDF 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pymupdf", "-q"], check=True)
        print("[paper-analysis] PyMuPDF 安装完成")


def download_pdf(url: str, output_path: str, timeout: int = 60) -> bool:
    """下载 PDF 到本地文件"""
    print(f"[paper-analysis] 下载 PDF: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PaperAnalysisBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp, \
                open(output_path, "wb") as out:
            out.write(resp.read())
        size = os.path.getsize(output_path) / 1024
        print(f"[paper-analysis] 下载完成: {output_path} ({size:.1f} KB)")
        return True
    except Exception as e:
        print(f"[paper-analysis] 下载失败: {e}")
        return False


def extract_text_from_pdf(pdf_path: str) -> tuple[str, int]:
    """用 PyMuPDF 提取 PDF 全文文本"""
    import fitz
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    full_text = "\n".join(text_parts)
    return full_text, len(doc)


def parse_paper_text(text: str) -> dict:
    """从论文全文中结构化提取信息"""
    result = {
        "arxiv_id": "",
        "venue": "",
        "title": "",
        "background": "",
        "innovation_points": [],
        "datasets": [],
        "metrics": {},
        "hyperparams": {},
        "arch_params": {},
        "tables": {},
        "score": 50,
    }

    # --- 1. arXiv ID / Venue ---
    arxiv_matches = re.findall(r"arXiv:(\d{4}\.\d{4,})", text[:5000])
    if arxiv_matches:
        result["arxiv_id"] = arxiv_matches[0]

    venue_match = re.search(
        r"(NeurIPS|ICLR|CVPR|ICCV|ECCV|ICML|AAAI|IJCAI|arxiv)",
        text[:3000], re.IGNORECASE
    )
    if venue_match:
        v = venue_match.group(1).upper()
        result["venue"] = v if v != "ARXIV" else "arXiv preprint"

    # --- 2. Abstract ---
    abstract_match = re.search(
        r"ABSTRACT\s*(.*?)(?:\n\n|\n\s*1\s*INTRODUCTION|INTRODUCTION)",
        text, re.DOTALL | re.IGNORECASE
    )
    if not abstract_match:
        abstract_match = re.search(
            r"摘要\s*(.*?)(?:1\s*引言|INTRODUCTION)", text, re.DOTALL
        )
    if abstract_match:
        result["background"] = abstract_match.group(1).strip()[:2000]
        # 提取创新点句子
        sentences = re.split(r"(?<=[.!?])\s+", result["background"])
        result["innovation_points"] = [
            s.strip() for s in sentences
            if len(s.strip()) > 40 and any(
                kw in s.lower() for kw in ["propose", "introduce", "present", "novel", "new"]
            )
        ][:5]

    # --- 3. 数据集 ---
    dataset_map = [
        (r"COCO\b", "COCO"),
        (r"ImageNet\b", "ImageNet"),
        (r"LAION", "LAION"),
        (r"MSCOCO|MS COCO", "MS COCO"),
        (r"ADE20K", "ADE20K"),
        (r"PuzzleIOI", "PuzzleIOI"),
        (r"4D-Dress|4D Dress", "4D-Dress"),
        (r"THuman2\.1|THuman", "THuman2.1"),
        (r"Human4DiT", "Human4DiT"),
        (r"CustomHumans", "CustomHumans"),
        (r"\b2K2K\b", "2K2K"),
        (r"PuzzleAvatar", "PuzzleAvatar"),
        (r"PSHuman", "PSHuman"),
        (r"\bECON\b", "ECON"),
        (r"PIFuHD", "PIFuHD"),
        (r"Human3Diff", "Human3Diff"),
        (r"Icon", "ICON"),
    ]
    found_datasets = set()
    for pattern, name in dataset_map:
        if re.search(pattern, text, re.IGNORECASE):
            found_datasets.add(name)
    result["datasets"] = sorted(found_datasets)

    # --- 4. 评测指标 ---
    metric_keywords = [
        "PSNR", "SSIM", "LPIPS", "FID", "CLIP-I", "DINO",
        "Chamfer", "P2S", "Normal", "V2V",
        "Accuracy", "Recall", "Precision", "F1",
        "IoU", "mAP", "AUC",
    ]
    found_metrics = []
    for kw in metric_keywords:
        if re.search(r"\b" + kw + r"\b", text, re.IGNORECASE):
            found_metrics.append(kw)
    result["metrics"]["available"] = found_metrics

    # --- 5. 训练超参数 ---
    # Learning Rate
    lr_vals = []
    for pattern in [
        r"learning\s*rate[:\s=]*([0-9.e\-+]+)",
        r"lr[:\s=]*([0-9.e\-+]+)",
        r"([0-9.e\-+]+)\s*[\*x]\s*10\s*[-]\s*[4-6]\b.*\blr\b",
        r"lr\s*=\s*([0-9.e\-+]+)",
    ]:
        for m in re.finditer(pattern, text[:150000], re.IGNORECASE):
            try:
                f = float(m.group(1))
                if 1e-8 <= f <= 1e-1:
                    lr_vals.append(f)
            except ValueError:
                pass
    if lr_vals:
        result["hyperparams"]["learning_rate"] = min(lr_vals)

    # Batch Size
    bs_vals = []
    for pattern in [r"batch\s*size[:\s=]*(\d+)", r"bs[:\s=]*(\d+)"]:
        for m in re.finditer(pattern, text[:150000], re.IGNORECASE):
            try:
                bs_vals.append(int(m.group(1)))
            except ValueError:
                pass
    if bs_vals:
        result["hyperparams"]["batch_size"] = max(set(bs_vals), key=bs_vals.count)

    # Epochs
    ep_vals = []
    for m in re.finditer(r"(\d+)\s*(?:epoch|iterations|steps)", text[:150000], re.IGNORECASE):
        try:
            ep_vals.append(int(m.group(1)))
        except ValueError:
            pass
    if ep_vals:
        result["hyperparams"]["epochs"] = max(set(ep_vals), key=ep_vals.count)

    # --- 6. 数值表格（简化行级提取） ---
    table_blocks = re.findall(
        r"(?:Table\s+\d+[^\n]*\n)(.*?)(?=\n\s*\n|\Z)",
        text, re.DOTALL
    )
    for i, block in enumerate(table_blocks[:8]):
        rows = [r.strip() for r in block.split("\n") if r.strip()]
        if len(rows) >= 2:
            result["tables"][f"table_{i+1}"] = rows[:15]

    # --- 7. 综合评分 ---
    score = 50
    score += min(20, len(result["datasets"]) * 3)
    score += min(15, len(found_metrics) * 2)
    if result["hyperparams"].get("learning_rate"):
        score += 5
    if result["hyperparams"].get("batch_size"):
        score += 5
    if result.get("tables"):
        score += 10
    result["score"] = min(100, score)

    return result


MD_CODE = "```"


def build_markdown_report(paper_name: str, info: dict) -> str:
    """生成 Markdown 格式报告"""
    lines = [
        f"# {paper_name}",
        "",
        "## 基本信息",
        f"- arXiv ID: `{info.get('arxiv_id', 'N/A')}`",
        f"- Venue: {info.get('venue', 'N/A')}",
        f"- 综合评分: **{info.get('score', 'N/A')}/100**",
        "",
        "## 研究背景与创新点",
        "",
    ]

    if info.get("innovation_points"):
        for pt in info["innovation_points"]:
            lines.append(f"- {pt}")
        lines.append("")

    if info.get("background"):
        bg = info["background"][:800].replace("\n", " ")
        lines.append(f"> {bg}")
        lines.append("")

    lines.append("## 实验设置")
    if info.get("datasets"):
        lines.append("### 数据集")
        for ds in info["datasets"]:
            lines.append(f"- {ds}")
        lines.append("")

    metrics_available = info.get("metrics", {}).get("available", [])
    if metrics_available:
        lines.append("### 评测指标")
        lines.append(", ".join(metrics_available))
        lines.append("")

    if info.get("tables"):
        lines.append("## 核心数值表格")
        for name, rows in info["tables"].items():
            lines.append(f"### {name}")
            for row in rows:
                lines.append(MD_CODE)
                lines.append(row)
                lines.append(MD_CODE)
            lines.append("")

    if info.get("hyperparams"):
        lines.append("## 训练超参数")
        for k, v in info["hyperparams"].items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    return "\n".join(lines)


def infer_paper_name(url: str) -> str:
    parts = url.rstrip("/").split("/")
    repo = parts[-1] if parts else "paper"
    for suffix in ["-main", "-master", "_main"]:
        repo = repo.removesuffix(suffix)
    return repo


def main():
    parser = argparse.ArgumentParser(description="paper-analysis: 自动论文解析工具")
    parser.add_argument("--github-url", type=str, default="")
    parser.add_argument("--paper-url", type=str, default="")
    parser.add_argument("--paper-path", type=str, default="")
    parser.add_argument("--output-root", type=str, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output-dir", type=str, default="",
                        help="直接指定输出目录（覆盖 output-root 的默认路径计算）")
    parser.add_argument("--paper-name", type=str, default="")
    args = parser.parse_args()

    ensure_deps()

    pdf_path = args.paper_path
    pdf_source = ""

    if not pdf_path:
        if args.paper_url:
            pdf_source = "paper_url"
        elif args.github_url:
            pdf_source = "github"
        else:
            print("[paper-analysis] 错误: 请提供 --paper-url 或 --github-url 或 --paper-path")
            sys.exit(1)

    paper_name = args.paper_name or infer_paper_name(args.github_url or args.paper_url or "")
    # 优先使用 --output-dir，否则默认输出到 {output_root}/{paper_name}/
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(args.output_root) / paper_name
    output_dir.mkdir(parents=True, exist_ok=True)

    if pdf_source == "paper_url":
        pdf_local = str(output_dir / "paper.pdf")
        if not download_pdf(args.paper_url, pdf_local):
            sys.exit(1)
        pdf_path = pdf_local
    elif pdf_source == "github":
        print(f"[paper-analysis] 从 GitHub 解析论文: {args.github_url}")
        try:
            req = urllib.request.Request(
                args.github_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                readme = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"[paper-analysis] GitHub README 获取失败: {e}")
            sys.exit(1)

        arxiv_url = None
        for pattern in [
            r"https://arxiv\.org/pdf/([0-9\.]+)",
            r"https://arxiv\.org/abs/([0-9\.]+)",
            r"arxiv\.org/abs/([0-9\.]+)",
        ]:
            m = re.search(pattern, readme, re.IGNORECASE)
            if m:
                arxiv_id = m.group(1)
                arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                break

        if not arxiv_url:
            print("[paper-analysis] 错误: 无法从 GitHub README 找到 arXiv 链接")
            sys.exit(1)

        print(f"[paper-analysis] 找到 arXiv PDF: {arxiv_url}")
        pdf_local = str(output_dir / "paper.pdf")
        if not download_pdf(arxiv_url, pdf_local):
            sys.exit(1)
        pdf_path = pdf_local

    # --- 提取文本 ---
    print(f"[paper-analysis] 解析 PDF: {pdf_path}")
    full_text, num_pages = extract_text_from_pdf(pdf_path)
    print(f"[paper-analysis] 提取完成: {num_pages} 页, {len(full_text)} 字符")

    text_path = output_dir / "paper_text.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[paper-analysis] 原始文本已保存: {text_path}")

    # --- 结构化解析 ---
    print("[paper-analysis] 结构化信息提取...")
    info = parse_paper_text(full_text)
    info["paper_name"] = paper_name

    # --- 生成报告 ---
    report_md = build_markdown_report(paper_name, info)
    report_path = output_dir / f"{paper_name}_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"[paper-analysis] 报告已生成: {report_path}")

    # --- 摘要输出 ---
    print("\n" + "=" * 60)
    print(f"论文解析完成: {paper_name}")
    print(f"  arXiv ID: {info.get('arxiv_id', 'N/A')}")
    print(f"  Venue: {info.get('venue', 'N/A')}")
    print(f"  评分: {info.get('score', 'N/A')}/100")
    print(f"  数据集: {', '.join(info.get('datasets', []))}")
    print(f"  指标: {', '.join(info.get('metrics', {}).get('available', []))}")
    if info.get("hyperparams"):
        print(f"  超参数: {info['hyperparams']}")
    print(f"  报告: {report_path}")
    print("=" * 60)

    # --- JSON 输出 ---
    result = {
        "paper_name": paper_name,
        "arxiv_id": info.get("arxiv_id", ""),
        "venue": info.get("venue", ""),
        "score": info.get("score", 0),
        "metrics": info.get("metrics", {}),
        "hyperparams": info.get("hyperparams", {}),
        "datasets": info.get("datasets", []),
        "innovation_points": info.get("innovation_points", []),
        "tables": info.get("tables", {}),
        "report_path": str(report_path),
        "text_path": str(text_path),
    }
    print("\n[JSON_RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("[/JSON_RESULT]")


if __name__ == "__main__":
    main()
