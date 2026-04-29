import os
import sys
import subprocess

# 自愈安装
try:
    import docx
    from docx.shared import Pt, RGBColor, Cm, Inches
    from docx.oxml.ns import qn, nsdecls
    from docx.oxml import parse_xml
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx", "-q"])
    import docx
    from docx.shared import Pt, RGBColor, Cm, Inches
    from docx.oxml.ns import qn, nsdecls
    from docx.oxml import parse_xml
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT


# ───────── 字体工具 ─────────

def _set_run_font(run, font_en='Times New Roman', font_cn='SimSun', size_pt=11, bold=False, color=None):
    """对单个 run 精确设置中英文字体、字号、加粗、颜色"""
    run.font.name = font_en
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    # 东亚字体 (w:eastAsia) — 这才是 Word 渲染中文时真正读取的属性
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} />')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), font_cn)
    rFonts.set(qn('w:ascii'), font_en)
    rFonts.set(qn('w:hAnsi'), font_en)
    if color:
        run.font.color.rgb = color


def _set_paragraph_font(paragraph, font_en='Times New Roman', font_cn='SimSun', size_pt=11, bold=False, color=None):
    """对段落中已有的所有 run 批量设置字体"""
    for run in paragraph.runs:
        _set_run_font(run, font_en, font_cn, size_pt, bold, color)


def _add_styled_paragraph(doc, text, font_en='Times New Roman', font_cn='SimSun', size_pt=11, bold=False, color=None, alignment=None, space_after_pt=6):
    """添加一段文本并精确控制字体"""
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_run_font(run, font_en, font_cn, size_pt, bold, color)
    if alignment is not None:
        p.alignment = alignment
    p.paragraph_format.space_after = Pt(space_after_pt)
    return p


def _add_styled_heading(doc, text, level=1, font_en='Times New Roman', font_cn='SimHei', size_pt=None, color=None):
    """
    添加标题并精确设置字体。
    python-docx 的 add_heading 会自动创建 run，我们再覆写字体。
    标题默认用黑体 (SimHei)，正文默认用宋体 (SimSun)。
    """
    size_map = {0: 22, 1: 16, 2: 14, 3: 12}
    if size_pt is None:
        size_pt = size_map.get(level, 12)
    heading = doc.add_heading(level=level)
    run = heading.add_run(text)
    _set_run_font(run, font_en, font_cn, size_pt, bold=True, color=color or RGBColor(0x00, 0x00, 0x00))
    return heading


def _set_default_font(doc, font_en='Times New Roman', font_cn='SimSun', size_pt=11):
    """设置文档默认字体 (Normal style)，作为兜底"""
    style = doc.styles['Normal']
    style.font.name = font_en
    style.font.size = Pt(size_pt)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")} />')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), font_cn)
    rFonts.set(qn('w:ascii'), font_en)
    rFonts.set(qn('w:hAnsi'), font_en)


def _set_cell_font(cell, font_en='Times New Roman', font_cn='SimSun', size_pt=10.5, bold=False):
    """设置表格单元格内所有段落的字体"""
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            _set_run_font(run, font_en, font_cn, size_pt, bold)


def _shade_cells(cells, color_hex='D9E2F3'):
    """给单元格加底色"""
    for cell in cells:
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
        cell._element.get_or_add_tcPr().append(shading)


# ───────── Markdown 导出 ─────────

def _export_markdown(repo_name, project_profile, implementation_steps, results_comparison, optimization_suggestions):
    """将报告数据渲染为 Markdown 文本"""
    lines = []
    lines.append(f'# 【复现报告】{repo_name}\n')

    # 一、项目简介
    lines.append('## 一、项目简介\n')
    lines.append(str(project_profile).strip() + '\n')

    # 二、复现实施步骤
    lines.append('## 二、复现实施步骤\n')
    steps_map = [
        ('2.1 代码获取', 'code_fetch'),
        ('2.2 环境搭建与排坑记录', 'env_setup'),
        ('2.3 数据与参数配置', 'data_params'),
        ('2.4 训练/推理核心流程', 'core_loop'),
        ('2.5 评估流程', 'eval_process'),
    ]
    for title_str, key in steps_map:
        lines.append(f'### {title_str}\n')
        content = str(implementation_steps.get(key, '未提供信息')).strip()
        lines.append(content + '\n')

    # 三、结果对比
    lines.append('## 三、结果对比（原论文 vs 当前复现）\n')
    if results_comparison and len(results_comparison) > 0:
        lines.append('| 评估维度/指标 | 官方/原论文基准 | 本次实际复现值 |')
        lines.append('|---|---|---|')
        for item in results_comparison:
            m = str(item.get('metric_name', '-'))
            o = str(item.get('official_value', '-'))
            r = str(item.get('reproduced_value', '-'))
            lines.append(f'| {m} | {o} | {r} |')
        lines.append('')
    else:
        lines.append('⚠️ 本次复现未捕获到可用于对比的量化指标数据。\n')

    # 四、优化建议
    lines.append('## 四、后期全量训练与优化建议\n')
    lines.append(str(optimization_suggestions).strip() + '\n')

    return '\n'.join(lines)


# ───────── 主生成函数 ─────────

def generate_report(
    repo_name,
    project_profile,
    implementation_steps,
    results_comparison,
    optimization_suggestions,
    font_english='Times New Roman',
    font_chinese='SimSun',
    readme_params=None
):
    """
    生成工业级复现报告 Word 文档。

    字体策略:
      - 正文中文: SimSun (宋体) — Windows/macOS/WPS 均内置，无需额外安装
      - 标题中文: SimHei (黑体) — 同上
      - 英文/数字: Times New Roman
      - 旧参数 '微软雅黑' 自动映射为 SimSun，避免 Linux 缺字体问题

    为什么不用"微软雅黑"：
      1. 微软雅黑是 Windows Vista+ 专属字体，Linux 生成环境通常没有
      2. python-docx 只把字体名写进 XML，不嵌入字体文件
      3. 如果打开方没有该字体 → Word/WPS 会 fallback 到默认字体，排版全乱
      4. 宋体 (SimSun) + 黑体 (SimHei) 是学术报告标配，且跨平台兼容性最好
    """
    try:
        # 字体兼容映射
        cn_font_map = {
            '微软雅黑': 'SimSun',
            'Microsoft YaHei': 'SimSun',
        }
        font_cn_body = cn_font_map.get(font_chinese, font_chinese)
        font_cn_heading = 'SimHei'  # 标题始终用黑体
        font_en = font_english

        doc = docx.Document()

        # 全局默认字体
        _set_default_font(doc, font_en, font_cn_body, 11)

        # ═══════ 封面标题 ═══════
        _add_styled_paragraph(doc, '', size_pt=11)  # 空行
        title_p = _add_styled_paragraph(
            doc,
            f'【复现报告】{repo_name}',
            font_en=font_en, font_cn='SimHei', size_pt=22, bold=True,
            alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after_pt=4
        )
        _add_styled_paragraph(
            doc,
            '自动化复现报告',
            font_en=font_en, font_cn='SimHei', size_pt=16, bold=False,
            alignment=WD_ALIGN_PARAGRAPH.CENTER, space_after_pt=12
        )

        # ═══════ 一、项目简介 ═══════
        _add_styled_heading(doc, '一、项目简介', level=1, font_en=font_en, font_cn=font_cn_heading)
        # 项目档案可能较长，按段落分割
        for para_text in str(project_profile).split('\n'):
            para_text = para_text.strip()
            if para_text:
                _add_styled_paragraph(doc, para_text, font_en=font_en, font_cn=font_cn_body, size_pt=11)

        # ═══════ 二、复现实施步骤 ═══════
        _add_styled_heading(doc, '二、复现实施步骤', level=1, font_en=font_en, font_cn=font_cn_heading)

        steps_map = [
            ('2.1 代码获取', 'code_fetch'),
            ('2.2 环境搭建与排坑记录', 'env_setup'),
            ('2.3 数据与参数配置', 'data_params'),
            ('2.4 训练/推理核心流程', 'core_loop'),
            ('2.5 评估流程', 'eval_process'),
        ]
        for title_str, key in steps_map:
            _add_styled_heading(doc, title_str, level=2, font_en=font_en, font_cn=font_cn_heading)
            content = str(implementation_steps.get(key, '未提供信息'))
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    _add_styled_paragraph(doc, line, font_en=font_en, font_cn=font_cn_body, size_pt=11)

        # ═══════ 三、结果对比 ═══════
        _add_styled_heading(doc, '三、结果对比（原论文 vs 当前复现）', level=1, font_en=font_en, font_cn=font_cn_heading)

        if results_comparison and len(results_comparison) > 0:
            table = doc.add_table(rows=1, cols=3)
            table.style = 'Table Grid'
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # 表头
            headers = ['评估维度 / 指标', '官方 / 原论文基准', '本次实际复现值']
            hdr_cells = table.rows[0].cells
            for i, h in enumerate(headers):
                hdr_cells[i].text = h
                _set_cell_font(hdr_cells[i], font_en, font_cn_body, 10.5, bold=True)
            _shade_cells(hdr_cells, 'D9E2F3')

            # 数据行
            for item in results_comparison:
                row_cells = table.add_row().cells
                row_cells[0].text = str(item.get('metric_name', '-'))
                row_cells[1].text = str(item.get('official_value', '-'))
                row_cells[2].text = str(item.get('reproduced_value', '-'))
                for cell in row_cells:
                    _set_cell_font(cell, font_en, font_cn_body, 10.5, bold=False)
        else:
            _add_styled_paragraph(
                doc, '⚠️ 本次复现未捕获到可用于对比的量化指标数据。',
                font_en=font_en, font_cn=font_cn_body, size_pt=11
            )

        # ═══════ 四、优化建议 ═══════
        _add_styled_heading(doc, '四、后期全量训练与优化建议', level=1, font_en=font_en, font_cn=font_cn_heading)
        for line in str(optimization_suggestions).split('\n'):
            line = line.strip()
            if line:
                _add_styled_paragraph(doc, line, font_en=font_en, font_cn=font_cn_body, size_pt=11)

        # ═══════ 保存 DOCX ═══════
        save_dir = f"/workspace/.openclaw/workspace/{repo_name}"
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{repo_name}_Final_Repro_Report.docx")
        doc.save(save_path)

        # ═══════ 保存 Markdown 副本 ═══════
        md_text = _export_markdown(
            repo_name, project_profile, implementation_steps,
            results_comparison, optimization_suggestions
        )
        md_dir = f"/workspace/user-data/codelab/{repo_name}/code"
        os.makedirs(md_dir, exist_ok=True)
        md_path = os.path.join(md_dir, f"{repo_name}_Final_Repro_Report.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_text)

        # ═══════ 生成 README.md ═══════
        readme_path = None
        if readme_params and isinstance(readme_params, dict):
            from readme_generator import generate_readme
            readme_content = generate_readme(
                repo_name=repo_name,
                project_title=readme_params.get('project_title', repo_name),
                project_summary=readme_params.get('project_summary', project_profile),
                project_highlights=readme_params.get('project_highlights', ''),
                repro_quickstart=readme_params.get('repro_quickstart', '')
            )
            readme_dir = f"/workspace/user-data/codelab/{repo_name}"
            os.makedirs(readme_dir, exist_ok=True)
            readme_path = os.path.join(readme_dir, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

        result_msg = (
            f"✅ 报告排版成功！已生成 Word + Markdown 双格式报告：\n"
            f"  📄 DOCX: `{save_path}`\n"
            f"  📝 MD:   `{md_path}`"
        )
        if readme_path:
            result_msg += f"\n  📖 README: `{readme_path}`"
        return result_msg

    except Exception as e:
        return f"❌ 报告生成遭遇底层失败：{str(e)}"
