import sys
import subprocess
import time

# ==========================================
# 🚀 极客级自愈：如果环境没装 paramiko，自动静默安装
# ==========================================
try:
    import paramiko
except ImportError:
    print("⏳ 未检测到 paramiko 库，正在后台自动静默安装...")
    # 使用 sys.executable 确保安装在 OpenClaw 当前运行的 Python 环境中
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko  # 安装完毕后重新导入


# ==========================================
# 核心执行逻辑
# ==========================================
def run_ssh_cmd(host, port, username, password, command):
    if "conda create -n " in command:
        command = command.replace("conda create -n ", "conda create -p /workspace/envs/ ")
    if "/opt/conda/envs/" in command:
        command = command.replace("/opt/conda/envs/", "/workspace/envs/")
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    max_retries = 30
    retry_delay = 10
    
    # 探活与连接逻辑
    for attempt in range(max_retries):
        try:
            print(f"⏳ 正在尝试连接 {host}:{port} (尝试 {attempt+1}/{max_retries})...")
            # timeout 设为 10 秒，防止单次连接死等
            ssh.connect(host, port=int(port), username=username, password=password, timeout=10)
            print("🎉 SSH 连接成功！开始执行命令...")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return f"❌ SSH 连接失败，已超时(5分钟)：{str(e)}"
    
    # 执行命令逻辑
    try:
        # 执行命令，组合多个命令时依赖 \n 或 &&
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # recv_exit_status() 会阻塞直到命令执行完成
        exit_status = stdout.channel.recv_exit_status() 
        
        out = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        
        result = f"✅ 执行完成 (Exit Code: {exit_status})\n"
        if out: result += f"========== [STDOUT] ==========\n{out}\n"
        if err: result += f"========== [STDERR] ==========\n{err}\n"
        
        return result
    except Exception as e:
        return f"❌ 命令执行异常：{str(e)}"
    finally:
        ssh.close()