import os
import subprocess
import tempfile
import json

# =============================================
# 大象库清单：源码编译极慢，优先用 apt 预编译包
# =============================================
ELEPHANT_LIBS = {
    "vtk":      {"apt": "libvtk9-dev",       "cmake_components": "CommonCore CommonDataModel IOXML"},
    "opencv":   {"apt": "libopencv-dev"},
    "boost":    {"apt": "libboost-all-dev"},
    "cgal":     {"apt": "libcgal-dev"},
    "pcl":      {"apt": "libpcl-dev"},
    "itk":      {"apt": "libinsighttoolkit5-dev"},
}

# =============================================
# 系统基础开发库（GL/X11/编译工具）
# =============================================
SYSTEM_DEV_PACKAGES = (
    "libopengl-dev libegl1-mesa-dev libglu1-mesa-dev libxt-dev "
    "libxext-dev libxrender-dev libxrandr-dev libxi-dev "
    "libxcursor-dev libxinerama-dev libxcomposite-dev libxdamage-dev "
    "libxfixes-dev libxss-dev libxft-dev libxmu-dev "
    "zip autoconf autoconf-archive pkg-config"
)


def run_remote_prep(ssh_ip, ssh_port, ssh_password, repo_name,
                    python_version="3.10", dependency_cmds=None,
                    data_cmds=None, weight_cmds=None,
                    vcpkg_json_path=None, enable_elephant_detect=True):
    """
    在远程 Lab4AI 实例上一站式完成项目准备：
    0. 系统基础开发库预装 + CMake 升级检测
    1. 检测并创建 Conda 环境（已存在则跳过）
    1b. 大象库检测与 apt 预编译替代（若项目含 vcpkg.json）
    1c. CUDA 特性剥离（CPU 实例无 GPU）
    2. 安装依赖（dependency_cmds）
    3. 下载数据（data_cmds）
    4. 下载权重（weight_cmds）
    """
    dependency_cmds = dependency_cmds or []
    data_cmds = data_cmds or []
    weight_cmds = weight_cmds or []

    base_dir = f"/workspace/user-data/codelab/{repo_name}"
    code_dir = f"{base_dir}/code"
    data_dir = f"{base_dir}/dataset"
    model_dir = f"{base_dir}/model"
    conda_env_path = f"/workspace/envs/{repo_name}"

    script_lines = [
        "#!/bin/bash",
        "set -e",
        "echo '========================================='",
        "echo '🚀 开始远程节点项目初始化 (环境/数据/权重)'",
        "echo '========================================='",
        "export http_proxy=http://10.201.85.65:1080",
        "export https_proxy=http://10.201.85.65:1080",
        "export CUDA_HOME=/usr/local/cuda",
        "export PATH=$CUDA_HOME/bin:$PATH",
        "",
        # ============================================
        # Phase 0: 系统基础开发库预装 + CMake 升级
        # ============================================
        "echo '👉 [0/8] 系统基础开发库预装（GL/X11/编译工具）...'",
        f"apt-get update -qq && apt-get install -y -qq {SYSTEM_DEV_PACKAGES} 2>/dev/null || echo '⚠️ 部分系统包安装失败，继续执行'",
        "",
        "# CMake 版本检测，低于 3.28 自动升级",
        "CMAKE_VER=$(cmake --version 2>/dev/null | head -1 | grep -oP '[0-9]+\\.[0-9]+' | head -1 || echo '0.0')",
        "CMAKE_MAJOR=$(echo $CMAKE_VER | cut -d. -f1)",
        "CMAKE_MINOR=$(echo $CMAKE_VER | cut -d. -f2)",
        "if [ \"$CMAKE_MAJOR\" -lt 3 ] || ([ \"$CMAKE_MAJOR\" -eq 3 ] && [ \"$CMAKE_MINOR\" -lt 28 ]); then",
        "  echo '⚠️ CMake $CMAKE_VER 过低，升级到最新版...'",
        "  pip install cmake --upgrade -q 2>/dev/null || echo '⚠️ CMake 升级失败，继续使用系统版'",
        "  # 把 pip 安装的 cmake 加入 PATH",
        "  PIP_CMAKE=$(python3 -c 'import cmake; print(cmake.CMAKE_BIN_DIR)' 2>/dev/null || true)",
        "  if [ -n \"$PIP_CMAKE\" ] && [ -f \"$PIP_CMAKE/cmake\" ]; then",
        "    export PATH=$PIP_CMAKE:$PATH",
        "    echo '✅ CMake 已升级到 '$(cmake --version | head -1)",
        "  fi",
        "else",
        "  echo '✅ CMake $CMAKE_VER 版本满足要求'",
        "fi",
        "",
        "echo '👉 [1/8] 检测并创建隔离的 Conda 虚拟环境...'",
        f"if [ -d '{conda_env_path}' ] && [ -f '{conda_env_path}/bin/python' ]; then",
        f"  echo '✅ Conda 环境已存在: {conda_env_path}，跳过创建'",
        "else",
        f"  echo '创建新环境: python={python_version}'",
        f"  /opt/conda/bin/conda create --prefix {conda_env_path} python={python_version} -y > /dev/null",
        "fi",
        f"source /opt/conda/bin/activate {conda_env_path}",
        "echo '📦 预装数据下载工具 (gdown)...'",
        "pip install gdown -q",
        f"echo '当前 Python: '$(python --version)",
        f"cd {code_dir}",
        "",
        "echo '🔗 确认目录结构与软链接...'",
        f"mkdir -p {data_dir} {model_dir}",
        # 在 code/ 内部创建标准软链接
        f"ln -sfn ../dataset {code_dir}/data 2>/dev/null || true",
        f"ln -sfn ../dataset {code_dir}/dataset 2>/dev/null || true",
        f"ln -sfn ../model {code_dir}/model 2>/dev/null || true",
        "",
        # 扫描项目配置文件中硬编码的 ../xxx 路径，在 code/ 内部创建兼容软链接
        "echo '🔍 扫描项目配置硬编码路径，动态创建兼容软链接...'",
        f"python3 << 'PATHSCAN_EOF'\n"
        f"import os, re, glob\n"
        f"code_dir = '{code_dir}'\n"
        f"data_target = '../dataset'\n"
        f"model_target = '../model'\n"
        f"config_files = []\n"
        f"for ext in ['yaml','yml','json','py','sh','cfg','ini','toml']:\n"
        f"    config_files.extend(glob.glob(os.path.join(code_dir, '**', f'*.{{ext}}'), recursive=True))\n"
        f"pattern = re.compile(r'\\.\\./(\\w[\\w-]*)')\n"
        f"found_dirs = set()\n"
        f"for fpath in config_files:\n"
        f"    try:\n"
        f"        with open(fpath, 'r', errors='ignore') as f:\n"
        f"            content = f.read()\n"
        f"        for m in pattern.findall(content):\n"
        f"            if m not in ('data','model','code'):\n"
        f"                found_dirs.add(m)\n"
        f"    except: pass\n"
        f"data_kw = ['dataset','datasets','corpus','input','inputs','raw_data','train_data','test_data','val_data']\n"
        f"model_kw = ['checkpoint','checkpoints','pretrained','pretrained_models','weights','ckpt','ckpts','saved_models','human_models']\n"
        f"created = []\n"
        f"for d in found_dirs:\n"
        f"    link_path = os.path.join(code_dir, d)\n"
        f"    if os.path.exists(link_path): continue\n"
        f"    dl = d.lower()\n"
        f"    if any(kw in dl for kw in model_kw):\n"
        f"        os.symlink(model_target, link_path)\n"
        f"        created.append(f'  {{d}} -> {{model_target}} (模型)')\n"
        f"    elif any(kw in dl for kw in data_kw):\n"
        f"        os.symlink(data_target, link_path)\n"
        f"        created.append(f'  {{d}} -> {{data_target}} (数据)')\n"
        f"if created:\n"
        f"    print('✅ 动态创建了以下兼容软链接:')\n"
        f"    for c in created: print(c)\n"
        f"else:\n"
        f"    print('ℹ️ 未发现需要额外创建的软链接')\n"
        f"PATHSCAN_EOF",
        ""
    ]

    # ============================================
    # Phase 1b: 大象库检测与 apt 预编译替代
    # ============================================
    if enable_elephant_detect and vcpkg_json_path:
        script_lines.append("echo '👉 [2/8] 大象库检测与预编译替代...'")
        script_lines.append(f"VCPKG_JSON='{vcpkg_json_path}'")
        script_lines.append("if [ -f \"$VCPKG_JSON\" ]; then")
        for lib_name, lib_info in ELEPHANT_LIBS.items():
            apt_pkg = lib_info["apt"]
            script_lines.append(f"  if grep -qi '\"{ lib_name}\"' \"$VCPKG_JSON\"; then")
            script_lines.append(f"    echo '🐘 检测到大象库 {lib_name}，用 apt 预编译包替代 vcpkg 源码编译...'")
            script_lines.append(f"    apt-get install -y -qq {apt_pkg} 2>/dev/null && echo '✅ {apt_pkg} 安装成功' || echo '⚠️ {apt_pkg} 安装失败'")
            # 从 vcpkg.json 中移除该依赖（用 python 做 JSON 操作更安全）
            script_lines.append(f"    python3 -c \"")
            script_lines.append(f"import json; f=open('$VCPKG_JSON','r'); d=json.load(f); f.close()")
            script_lines.append(f"deps=d.get('dependencies',[])")
            script_lines.append(f"new_deps=[x for x in deps if not (isinstance(x,str) and x=='{lib_name}') and not (isinstance(x,dict) and x.get('name')=='{lib_name}')]")
            script_lines.append(f"d['dependencies']=new_deps; f=open('$VCPKG_JSON','w'); json.dump(d,f,indent=2); f.close()")
            script_lines.append(f"print('✅ 已从 vcpkg.json 移除 {lib_name}')")
            script_lines.append(f"    \" || echo '⚠️ vcpkg.json 修改失败，手动检查'")
            script_lines.append("  fi")
        script_lines.append("else")
        script_lines.append("  echo '未找到 vcpkg.json，跳过大象库检测'")
        script_lines.append("fi")
    else:
        script_lines.append("echo '👉 [2/8] 大象库检测：未提供 vcpkg.json 或已禁用，跳过'")

    # ============================================
    # Phase 1c: CUDA 特性剥离（CPU 实例无 GPU）
    # ============================================
    if vcpkg_json_path:
        script_lines.append("echo '👉 [3/8] CUDA 特性剥离（CPU 实例无 GPU）...'")
        script_lines.append(f"VCPKG_JSON='{vcpkg_json_path}'")
        script_lines.append("if [ -f \"$VCPKG_JSON\" ]; then")
        # 用 python 脚本剥离所有 cuda 特性并记录到 cuda_features.json
        script_lines.append("  python3 -c \"")
        script_lines.append("import json,os")
        script_lines.append(f"vj='{vcpkg_json_path}'")
        script_lines.append("f=open(vj,'r'); d=json.load(f); f.close()")
        script_lines.append("stripped={}")
        script_lines.append("deps=d.get('dependencies',[])")
        script_lines.append("for i,dep in enumerate(deps):")
        script_lines.append("  if isinstance(dep,dict) and 'features' in dep:")
        script_lines.append("    cuda_feats=[ft for ft in dep['features'] if 'cuda' in ft.lower()]")
        script_lines.append("    if cuda_feats:")
        script_lines.append("      stripped[dep.get('name','unknown')]=cuda_feats")
        script_lines.append("      dep['features']=[ft for ft in dep['features'] if 'cuda' not in ft.lower()]")
        script_lines.append("      if not dep['features']: del dep['features']")
        script_lines.append("d['dependencies']=deps")
        script_lines.append("f=open(vj,'w'); json.dump(d,f,indent=2); f.close()")
        script_lines.append(f"cuda_record=os.path.dirname(vj)+'/cuda_features.json'")
        script_lines.append("f=open(cuda_record,'w'); json.dump(stripped,f,indent=2); f.close()")
        script_lines.append("if stripped: print('✅ 已剥离 CUDA 特性:',stripped)")
        script_lines.append("else: print('无 CUDA 特性需要剥离')")
        script_lines.append("  \" || echo '⚠️ CUDA 特性剥离失败，继续执行'")
        script_lines.append("fi")
        # 设置 vcpkg 优化参数
        script_lines.append("export VCPKG_MAX_CONCURRENCY=$(nproc)")
        script_lines.append("export VCPKG_BUILD_TYPE=release")
        script_lines.append("echo '✅ vcpkg 优化参数已设置: CONCURRENCY='$(nproc)', BUILD_TYPE=release'")
    else:
        script_lines.append("echo '👉 [3/8] CUDA 特性剥离：无 vcpkg.json，跳过'")

    # ============================================
    # Phase 2: 依赖安装（原 [2/4]）
    # ============================================
    if dependency_cmds:
        script_lines.append("echo '👉 [4/8] 开始安装项目核心依赖...'")
        for i, cmd in enumerate(dependency_cmds):
            script_lines.append(f"echo '[依赖 {i+1}/{len(dependency_cmds)}] {cmd}'")
            # 每条命令失败后重试 2 次
            script_lines.append(f"{{ {cmd}; }} || {{ echo '⚠️ 重试 1/2...'; sleep 5; {cmd}; }} || {{ echo '⚠️ 重试 2/2...'; sleep 5; {cmd}; }}")
    else:
        script_lines.append("echo '👉 [4/8] 无依赖命令，跳过'")

    if data_cmds:
        script_lines.append("echo '👉 [5/8] 开始下载与预处理数据集...'")
        for i, cmd in enumerate(data_cmds):
            script_lines.append(f"echo '[数据 {i+1}/{len(data_cmds)}] {cmd}'")
            script_lines.append(cmd)
    else:
        script_lines.append("echo '👉 [5/8] 无数据命令，跳过'")

    if weight_cmds:
        script_lines.append("echo '👉 [6/8] 开始下载预训练模型权重...'")
        # 🚨 统一注入 HF_ENDPOINT 环境变量，默认使用 hf-mirror.com 镜像
        script_lines.append("export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}")
        script_lines.append("echo '使用 HuggingFace 镜像: '$HF_ENDPOINT")
        for i, cmd in enumerate(weight_cmds):
            # huggingface-cli → hf 自动 fallback
            patched_cmd = cmd
            if 'huggingface-cli download' in cmd:
                hf_cmd = cmd.replace('huggingface-cli download', 'hf download')
                patched_cmd = f"{{ {hf_cmd}; }} || {{ echo '⚠️ hf 命令失败，尝试 huggingface-cli...'; {cmd}; }}"
            # 将 wget/curl HuggingFace URL 转换提醒（建议改用 hf_hub_download）
            elif ('wget' in cmd or 'curl' in cmd) and 'huggingface.co' in cmd:
                script_lines.append(f"echo '⚠️ 检测到 wget/curl 下载 HuggingFace 文件，建议改用 hf_hub_download Python API'")
            script_lines.append(f"echo '[权重 {i+1}/{len(weight_cmds)}] {cmd}'")
            # 权重下载也加重试
            script_lines.append(f"{{ {patched_cmd}; }} || {{ echo '⚠️ 重试 1/2...'; sleep 10; {patched_cmd}; }} || {{ echo '⚠️ 重试 2/2...'; sleep 10; {patched_cmd}; }}")
        # 🚨 下载后校验: 检查零字节权重文件
        script_lines.append(f"echo '📋 校验权重文件...'")
        script_lines.append(f"EMPTY_FILES=$(find {model_dir} -type f \\( -name '*.pt' -o -name '*.pth' -o -name '*.safetensors' -o -name '*.pkl' -o -name '*.bin' -o -name '*.npz' \\) -size 0 2>/dev/null)")
        script_lines.append(f"if [ -n \"$EMPTY_FILES\" ]; then echo '❌ 发现零字节权重文件:'; echo \"$EMPTY_FILES\"; exit 1; fi")
        script_lines.append(f"echo '✅ 权重文件校验通过 (无零字节文件)'")
    else:
        script_lines.append("echo '👉 [6/8] 无权重命令，跳过'")

    # ============================================
    # Phase 7: 依赖 import 级 Smoke Test
    # ============================================
    script_lines.append("echo '👉 [7/8] 依赖 import 级 Smoke Test...'")
    script_lines.append("echo '逐个测试已安装核心包的 import 是否正常...'")
    # 从 requirements.txt 提取顶层包名，做 import 检测
    script_lines.append(f"if [ -f '{code_dir}/requirements.txt' ]; then")
    script_lines.append(f"  FAILED_IMPORTS=''")
    script_lines.append(f"  for PKG in $(cat '{code_dir}/requirements.txt' | grep -v '^#' | grep -v '^$' | sed 's/[>=<\!].*//' | sed 's/\[.*//' | tr '-' '_' | head -30); do")
    script_lines.append(f"    python -c \"import $PKG\" 2>/dev/null || FAILED_IMPORTS=\"$FAILED_IMPORTS $PKG\"")
    script_lines.append(f"  done")
    script_lines.append(f"  if [ -n \"$FAILED_IMPORTS\" ]; then")
    script_lines.append(f"    echo '⚠️ 以下包 import 失败（可能是包名映射不同，非致命）:$FAILED_IMPORTS'")
    script_lines.append(f"  else")
    script_lines.append(f"    echo '✅ 所有 requirements.txt 包 import 检测通过'")
    script_lines.append(f"  fi")
    script_lines.append("else")
    script_lines.append("  echo '未找到 requirements.txt，跳过 import 检测'")
    script_lines.append("fi")

    # ============================================
    # Phase 8: 项目主包 dry-run 验证
    # ============================================
    script_lines.append("echo '👉 [8/8] 项目主包 dry-run 验证（import 级）...'")
    # 从 pyproject.toml / setup.py 推测主包名（用 repo_name 的常见变体）
    pkg_name_underscore = repo_name.replace('-', '_').lower()
    script_lines.append(f"# 尝试 import 项目主包（{pkg_name_underscore}）")
    script_lines.append(f"python -c 'import {pkg_name_underscore}; print(\"✅ 主包 {pkg_name_underscore} import 成功\")' 2>/dev/null || ")
    script_lines.append(f"  python -c 'import {repo_name.lower()}; print(\"✅ 主包 {repo_name.lower()} import 成功\")' 2>/dev/null || ")
    script_lines.append(f"  echo '⚠️ 主包 import 失败（可能需要 GPU 阶段 pip install -v . 编译安装，非致命）'")

    # ============================================
    # Phase 9: 项目根目录清理（硬性规定：只保留 code/ data/ model/ README.md）
    # ============================================
    script_lines.append("echo '🧹 [清理] 检查项目根目录规范性...'")
    script_lines.append(f"cd {base_dir}")
    # 列出根目录下所有项，删除不在白名单中的
    script_lines.append("for item in $(ls -A); do")
    script_lines.append("  case \"$item\" in")
    script_lines.append("    code|dataset|model|README.md) ;;")
    script_lines.append("    *) echo \"⚠️ 移除项目根目录下的非规范项: $item\"; rm -rf \"$item\" ;;")
    script_lines.append("  esac")
    script_lines.append("done")
    script_lines.append("echo '✅ 项目根目录已清理，只保留 code/ dataset/ model/ README.md'")

    script_lines.append("echo '========================================='")
    script_lines.append("echo '✅ 所有准备工作圆满完成！'")
    script_lines.append("echo '========================================='")

    # 写入临时脚本
    script_content = "\n".join(script_lines)
    fd, temp_script_path = tempfile.mkstemp(suffix=".sh")
    with os.fdopen(fd, 'w') as f:
        f.write(script_content)

    # SSH 执行
    ssh_cmd = [
        "sshpass", "-p", ssh_password,
        "ssh", "-o", "StrictHostKeyChecking=no", "-p", str(ssh_port),
        f"root@{ssh_ip}",
        "bash -s"
    ]

    try:
        with open(temp_script_path, "r") as f:
            result = subprocess.run(
                ssh_cmd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=7200  # 最长 2 小时
            )

        output_log = result.stdout
        os.remove(temp_script_path)

        if result.returncode == 0:
            return f"✅ 远程项目准备全部成功！\n\n【底层日志截取】:\n{output_log[-2000:]}"
        else:
            return f"❌ 远程执行报错 (Exit Code {result.returncode})。\n\n【完整错误日志】:\n{output_log}"

    except subprocess.TimeoutExpired:
        os.remove(temp_script_path)
        return "❌ 执行超时（超 2 小时），可能数据集过大或下载卡死。"
    except Exception as e:
        os.remove(temp_script_path)
        return f"❌ 系统级连接错误: {str(e)}"
