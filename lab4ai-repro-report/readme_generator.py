# README.md 模板生成器
# 在 generate_report 中自动生成项目 README.md

import os


def generate_readme(
    repo_name,
    project_title,
    project_summary,
    project_highlights,
    repro_quickstart=""
):
    """
    生成项目 README.md 内容。

    参数:
      repo_name: 项目名称（如 motion-guided-flow）
      project_title: 项目完整标题（如 MoFlow — 运动引导光流循环渲染帧预测）
      project_summary: 项目简介（1-3 段话，描述论文背景和核心创新）
      project_highlights: 项目要点（Markdown 格式，包含 2-4 个要点块）
      repro_quickstart: 可选的快速复现命令说明（Markdown 格式，可包含代码块）
    """
    lines = []
    lines.append(f'## 🎨 {project_title}')
    lines.append('')
    lines.append('### 📌 简介')
    lines.append('')
    lines.append(project_summary.strip())
    lines.append('')
    lines.append('#### ✅ 项目要点')
    lines.append('')
    lines.append(project_highlights.strip())
    lines.append('')
    lines.append('## 🛠️ 项目文件说明')
    lines.append('')
    lines.append(f'- 💻 代码获取：项目代码已存放于 `codelab/{repo_name}/code` 文件夹中。')
    lines.append('')
    lines.append(f'- 📊 数据文件：项目中使用的数据集存放于 `codelab/{repo_name}/dataset` 文件夹中。')
    lines.append('')
    lines.append(f'- 🏋️ 模型权重文件：项目中使用的模型权重存放于 `codelab/{repo_name}/model` 文件夹中。')
    lines.append('')
    lines.append(f'- 🌐 环境说明：运行所需环境已预安装在 `/workspace/envs/{repo_name}` 中，您无需进行任何额外的环境配置。')
    lines.append('')
    lines.append('## 🎯 体验与复现')
    lines.append('')
    lines.append(f'我们已将复现代码整合在 `/workspace/codelab/{repo_name}/code/{repo_name}_Final_Repro_Report.md` 文件中，直接执行该文件中的代码即可快速体验复现成果或者从0开始复现全过程，也可根据应用需要优化和改进。')
    lines.append('')
    if repro_quickstart and repro_quickstart.strip():
        lines.append(repro_quickstart.strip())
        lines.append('')
    lines.append('## 🚪 项目进入方式')
    lines.append('')
    lines.append('1. 点击对应项目名称链接，单击「立即体验」按钮。')
    lines.append('')
    lines.append('2. 选择项目进入方式：JupyterNotebook 或 VSCode。')
    lines.append('')
    lines.append('3. 选择 GPU/CPU 卡数启动环境，即可直接打开项目文件。')
    lines.append('')

    return '\n'.join(lines)
