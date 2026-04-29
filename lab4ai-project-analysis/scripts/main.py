import os
import re
import subprocess
import tempfile
import requests
import shutil

# ==========================================
# 🌐 内网穿透与动态代理配置
# ==========================================
LAB_PROXY = "http://10.201.85.65:1080"
PROXY_URL = os.environ.get("http_proxy", os.environ.get("HTTP_PROXY", LAB_PROXY))

os.environ["http_proxy"] = PROXY_URL
os.environ["https_proxy"] = PROXY_URL
REQ_PROXIES = {"http": PROXY_URL, "https": PROXY_URL}
REQ_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0"}

# ==========================================
# 🔒 Gated Model 镜像映射表
# ==========================================
GATED_MODEL_MIRRORS_PATH = os.path.join(
    os.path.expanduser("~"), ".openclaw", "workspace", "gated_model_mirrors.yaml"
)


def _load_gated_mirrors() -> dict:
    """加载 gated_model_mirrors.yaml，返回 {model_id: {mirrors: [...], status: ...}}"""
    if not os.path.exists(GATED_MODEL_MIRRORS_PATH):
        return {}
    try:
        import yaml
        with open(GATED_MODEL_MIRRORS_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        # 无 yaml 库时用简单正则解析
        result = {}
        current_key = None
        with open(GATED_MODEL_MIRRORS_PATH, "r") as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith(" ") and line.endswith(":"):
                    current_key = line[:-1].strip()
                    result[current_key] = {"mirrors": [], "status": "unknown"}
                elif current_key and "- " in line and "mirrors" not in line:
                    mirror = line.split("- ")[1].split("#")[0].strip()
                    if mirror:
                        result[current_key]["mirrors"].append(mirror)
                elif current_key and "status:" in line:
                    result[current_key]["status"] = line.split("status:")[1].strip()
        return result


def _scan_gated_models(project_dir: str) -> list:
    """
    扫描项目中所有 from_pretrained("xxx") 调用，
    检查 model_id 是否为 gated model，返回发现列表。
    """
    mirrors_db = _load_gated_mirrors()
    pattern = re.compile(r'from_pretrained\s*\(\s*["\']([^"\']+)["\']')
    default_pattern = re.compile(r'default\s*=\s*["\']([a-zA-Z0-9_-]+/[a-zA-Z0-9._-]+)["\']')
    # 过滤掉本地路径（含文件后缀或以 ./ 开头）
    LOCAL_PATH_SUFFIXES = ('.pt', '.pth', '.bin', '.safetensors', '.ckpt', '.index', '.json', '.onnx')

    def _is_hf_model_id(mid: str) -> bool:
        """判断是否为合法的 HuggingFace model_id (org/model 格式)"""
        if mid.startswith(('./', '../', '/')):
            return False
        if any(mid.endswith(s) for s in LOCAL_PATH_SUFFIXES):
            return False
        parts = mid.split('/')
        if len(parts) != 2:
            return False
        # org 和 model 都不应含 . (排除路径)
        return all(len(p) > 0 for p in parts)

    findings = []
    seen_ids = set()

    for root, _, files in os.walk(project_dir):
        if ".git" in root:
            continue
        for fname in files:
            if not fname.endswith((".py", ".yaml", ".yml", ".json")):
                continue
            filepath = os.path.join(root, fname)
            if os.path.getsize(filepath) > 2 * 1024 * 1024:
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_num, line in enumerate(fh, 1):
                        for m in list(pattern.finditer(line)) + list(default_pattern.finditer(line)):
                            model_id = m.group(1).strip()
                            if "/" in model_id and model_id not in seen_ids and _is_hf_model_id(model_id):
                                seen_ids.add(model_id)
                                entry = {
                                    "model_id": model_id,
                                    "file": os.path.relpath(filepath, project_dir),
                                    "line": line_num,
                                    "in_mirror_db": model_id in mirrors_db,
                                }
                                if model_id in mirrors_db:
                                    entry["mirrors"] = mirrors_db[model_id].get("mirrors", [])
                                    entry["status"] = mirrors_db[model_id].get("status", "unknown")
                                findings.append(entry)
            except Exception:
                pass

    # 在线探测 gated 状态 (仅对不在映射表中的 model_id)
    for item in findings:
        if item["in_mirror_db"]:
            item["gated"] = True
            continue
        try:
            resp = requests.get(
                f"https://huggingface.co/api/models/{item['model_id']}",
                timeout=5, proxies=REQ_PROXIES, headers=REQ_HEADERS
            )
            if resp.status_code == 200:
                data = resp.json()
                gated_val = data.get("gated", False)
                item["gated"] = gated_val not in (False, "false", None)
                item["gated_type"] = str(gated_val)
            elif resp.status_code == 401:
                item["gated"] = True
                item["gated_type"] = "requires_auth"
            elif resp.status_code == 404:
                item["gated"] = None
                item["gated_type"] = "not_found"
            else:
                item["gated"] = None
                item["gated_type"] = f"http_{resp.status_code}"
        except Exception:
            item["gated"] = None
            item["gated_type"] = "timeout"

    return findings


def audit_repo(repo_url: str) -> str:
    """OpenClaw 终极审计引擎：学术五大复现标准 + H100硬件适配性 + Gated Model 扫描"""
    report =[f"🔍 **开始对仓库 {repo_url} 进行 [六维深度静态审计]...**\n"]
    score = 100
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ---------------------------------------------------------
        # 📥 步骤 0: 深度克隆 (支持子模块，防丢文件)
        # ---------------------------------------------------------
        report.append("📥[1/6] 正在拉取代码库及子模块...")
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--recurse-submodules", repo_url, temp_dir],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60
            )
        except Exception as e:
            return f"❌ 克隆失败：{str(e)[:200]}"

        # ---------------------------------------------------------
        # 📦 维度一：环境与依赖的“绝对锚定” + H100 底层库排雷
        # ---------------------------------------------------------
        report.append("📦 [2/6] 检查【维度一：依赖锚定】与 H100 兼容性...")
        req_path = os.path.join(temp_dir, "requirements.txt")
        env_path = os.path.join(temp_dir, "environment.yml")
        has_old_torch = False
        
        if not (os.path.exists(req_path) or os.path.exists(env_path)):
            score -= 20
            report.append("  ❌ 严重：**未找到**标准的依赖文件 (requirements.txt / environment.yml)！(-20分)")
        elif os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                lines =[l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
                locked = sum(1 for l in lines if "==" in l or ">=" in l or "~=" in l)
                
                # 硬件排雷：H100 (sm_90) 不支持 PyTorch 1.x
                if any(re.search(r"torch(==|<=|<)1\.", l) for l in lines):
                    has_old_torch = True

                if lines and locked == 0:
                    score -= 10
                    report.append("  ⚠️ 警告：依赖未锁死版本号 (无 ==)，极易发生版本漂移 (-10分)")
                else:
                    report.append(f"  ✅ 依赖锁死度良好 ({locked}/{len(lines)})。")
                    
        if has_old_torch:
            score -= 20
            report.append("  ❌ 硬件致命缺陷：项目硬编码依赖 PyTorch 1.x。H100 架构必须使用 PyTorch >= 2.0，强行复现必报 CUDA Error！(-20分)")

        # ---------------------------------------------------------
        # 🕵️ 维度三/五/硬件：去个人化 + 随机性控制 + Hopper架构特征
        # ---------------------------------------------------------
        report.append("🖥️ [3/6] 检查【维度三/五：代码规范】与 Hopper 架构适配性...")
        hardcoded_paths =[]
        has_seed_control = False
        
        has_apex = False
        has_bf16 = False
        has_flash_attn = False
        has_sm90 = False
        
        path_regex = re.compile(r'(["\']\/home\/[a-zA-Z0-9_]+\/.*?["\'])|(["\']C:\\\\(?:Users)\\\\[a-zA-Z0-9_]+\\\\.*?["\'])')
        seed_regex = re.compile(r'(random\.seed|np\.random\.seed|torch\.manual_seed|cudnn\.deterministic)')
        
        for root, _, files in os.walk(temp_dir):
            if ".git" in root: continue
            for file in files:
                if file.endswith((".py", ".sh", ".yaml", ".cpp", ".cu")):
                    filepath = os.path.join(root, file)
                    if os.path.getsize(filepath) > 2 * 1024 * 1024: continue 
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f):
                                # 维度三：绝杀个人绝对路径
                                if path_regex.search(line): hardcoded_paths.append(f"`{file}` (行 {line_num+1})")
                                # 维度五：检查随机种子 (科学实验严谨性)
                                if seed_regex.search(line): has_seed_control = True
                                
                                # H100 架构雷点与亮点
                                if "apex.amp" in line or "from apex " in line: has_apex = True
                                if "bfloat16" in line or "bf16" in line: has_bf16 = True
                                if "flash_attn" in line or "FlashAttention" in line: has_flash_attn = True
                                if "sm_90" in line or "compute_90" in line: has_sm90 = True
                    except Exception:
                        pass
        
        if hardcoded_paths:
            score -= 15
            report.append(f"  ❌ 违规：写死了个人绝对路径 (-15分): {', '.join(hardcoded_paths[:3])}...")
        else:
            report.append("  ✅ 代码整洁，未发现明显的个人电脑绝对路径。")
            
        if not has_seed_control:
            score -= 5
            report.append("  ⚠️ 警告：未扫描到固定随机种子操作 (如 manual_seed)，复现精度可能有随机波动 (-5分)。")
        else:
            report.append("  ✅ 随机性控制：代码包含随机种子锁定，实验具备确定性基础。")

        if has_apex:
            score -= 15
            report.append("  ❌ 硬件严重缺陷：检测到已被弃用的 `NVIDIA Apex`。在 H100 上编译该 C++ 混合精度库会严重报错，需替换为 `torch.cuda.amp`！(-15分)")
            
        # H100 亮点反馈 (供 Agent 生成全量建议使用)
        if has_sm90: report.append("  🌟 架构前瞻：代码已针对 sm_90 (Hopper架构) 进行底层优化。")
        if has_bf16: report.append("  🌟 精度优化：支持 BF16 (bfloat16) 精度，完美契合 H100 第四代 Tensor Core。")
        if has_flash_attn: report.append("  🌟 算力解放：支持 FlashAttention，可充分榨干 H100 超高显存带宽！")

        # ---------------------------------------------------------
        # 🔗 维度二/四：执行闭环与数据公网存活 (最核心)
        # ---------------------------------------------------------
        report.append("🔗 [4/6] 检查【维度二/四：执行闭环与数据死链】...")
        readme_path = os.path.join(temp_dir, "README.md")
        if not os.path.exists(readme_path):
            score -= 30
            report.append("  ❌ 致命：完全没有 README.md 文件 (-30分)！")
        else:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                content_lower = content.lower()
                
                # 维度四：执行闭环 (Train + Eval)
                has_train = "train" in content_lower or "run " in content_lower or "python main.py" in content_lower
                has_eval = "eval" in content_lower or "test" in content_lower or "inference" in content_lower
                
                if not has_train:
                    score -= 10
                    report.append("  ⚠️ 闭环缺失：README 缺乏明确的 'train' 训练指令 (-10分)")
                if not has_eval:
                    score -= 10
                    report.append("  ⚠️ 闭环缺失：README 缺乏明确的 'eval/inference' 评估指令，无法验证精度对齐 (-10分)")
                if has_train and has_eval:
                    report.append("  ✅ 执行闭环完整：包含训练与评估的指导说明。")
                
                # 维度二：外部数据源连通性
                urls = list(set(re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s"\'\])]*', content)))
                dead_links = []
                for url in urls[:8]: # 限查8个防卡死
                    if any(domain in url for domain in["github.com", "arxiv.org", "doi.org"]): continue
                    try:
                        resp = requests.head(url, timeout=3, allow_redirects=True, proxies=REQ_PROXIES, headers=REQ_HEADERS)
                        if resp.status_code in [403, 405]:
                            resp = requests.get(url, timeout=3, stream=True, proxies=REQ_PROXIES, headers=REQ_HEADERS)
                        if resp.status_code >= 400: dead_links.append(f"{url} (HTTP {resp.status_code})")
                    except Exception:
                        dead_links.append(f"{url} (连接失败)")
                
                if dead_links:
                    deduct = min(len(dead_links) * 10, 30)
                    score -= deduct
                    report.append(f"  ❌ 严重：发现数据/权重外链失效 (-{deduct}分): {', '.join(dead_links)}")
                else:
                    report.append("  ✅ 数据与权重存活：文档中的外部链接初步检测连通性良好。")

        # ---------------------------------------------------------
        # 🔒 维度六：Gated Model / 受限模型扫描
        # ---------------------------------------------------------
        report.append("🔒 [5/6] 检查【维度六：模型可访问性 (Gated Model 扫描)】...")
        gated_findings = _scan_gated_models(temp_dir)

        if not gated_findings:
            report.append("  ✅ 未发现 from_pretrained() 调用引用外部 HuggingFace 模型，无 Gated 风险。")
        else:
            gated_blocked = [item for item in gated_findings if item.get("gated") is True]
            gated_unknown = [item for item in gated_findings if item.get("gated") is None]
            gated_ok = [item for item in gated_findings if item.get("gated") is False]

            if gated_ok:
                report.append(f"  ✅ 公开可访问模型 ({len(gated_ok)}):")
                for item in gated_ok:
                    report.append(f"    - `{item['model_id']}` ({item['file']}:{item['line']})")

            if gated_blocked:
                deduct = min(len(gated_blocked) * 10, 20)
                score -= deduct
                report.append(f"  ❌ 发现 Gated/受限模型 ({len(gated_blocked)}) (-{deduct}分):")
                for item in gated_blocked:
                    mirrors = item.get("mirrors", [])
                    if mirrors:
                        report.append(f"    - `{item['model_id']}` ({item['file']}:{item['line']}) → 🔄 可用镜像: {', '.join(mirrors)}")
                    else:
                        report.append(f"    - `{item['model_id']}` ({item['file']}:{item['line']}) → ⚠️ 无已知镜像，需 HF Token")

            if gated_unknown:
                report.append(f"  ⚠️ 无法确认访问性 ({len(gated_unknown)}):")
                for item in gated_unknown:
                    report.append(f"    - `{item['model_id']}` ({item['file']}:{item['line']}) — {item.get('gated_type', 'unknown')}")

        # ---------------------------------------------------------
        # 📊 生成终极总结
        # ---------------------------------------------------------
        score = max(0, score) # 防止扣成负数
        report.append(f"\n📊 **最终 H100 适配性与复现综合得分：{score} / 100**")
        if score >= 80: report.append("🟢 **结论：完美通过！代码严谨且高度适配 H100 架构。** 可放心拉起 H800A 算力进行全自动复现。")
        elif score >= 60: report.append("🟡 **结论：具备基础复现条件，但有隐患。** 请 Agent 重点修复扣分项 (如升级 PyTorch 或清理个人路径)。")
        else: report.append("🔴 **结论：学术垃圾/远古代码预警！** 不满足核心复现条件或无法兼容 H100，强烈建议熔断！")
        
        return "\n".join(report)
        
    finally:
        # 清理内存现场
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)