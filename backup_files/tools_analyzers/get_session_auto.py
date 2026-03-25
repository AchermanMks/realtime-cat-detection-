#!/usr/bin/env python3
"""
自动获取SessionId工具
尝试通过多种登录方式自动获取有效SessionId
"""

import subprocess
import json
import time
import os

def setup_ssl_compatibility():
    """设置SSL兼容性"""
    openssl_conf = '/tmp/openssl_legacy.conf'
    config_content = '''openssl_conf = openssl_init

[openssl_init]
ssl_conf = ssl_sect

[ssl_sect]
system_default = system_default_sect

[system_default_sect]
Options = UnsafeLegacyRenegotiation
'''

    with open(openssl_conf, 'w') as f:
        f.write(config_content)

    os.environ['OPENSSL_CONF'] = openssl_conf
    print("✅ SSL兼容性配置完成")

def try_login_method_1(username="admin", password="admin123"):
    """尝试登录方法1: /ipc/login API"""
    print("🔐 尝试登录方法1: API登录...")

    login_data = {
        "username": username,
        "password": password
    }

    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "10",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "-H", "Origin: https://192.168.31.146",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "--data-raw", json.dumps(login_data),
        "https://192.168.31.146/ipc/login"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print(f"   登录响应: {response}")

                # 检查是否成功
                if response.get('result') == 0:
                    param = response.get('param', {})
                    session_id = param.get('sessionid')
                    if session_id:
                        print(f"   ✅ 获取到SessionId: {session_id}")
                        return session_id

                print(f"   ❌ 登录失败: {response}")
                return None

            except json.JSONDecodeError:
                print(f"   ❌ 响应不是JSON: {result.stdout[:100]}")
                return None
        else:
            print(f"   ❌ 请求失败: {result.stderr}")
            return None

    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        return None

def try_login_method_2(username="admin", password="admin123"):
    """尝试登录方法2: 访问PTZ页面获取cookie"""
    print("🔐 尝试登录方法2: Web页面登录...")

    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "10",
        "-c", "/tmp/cookies.txt",  # 保存cookies
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        f"--user", f"{username}:{password}",
        "https://192.168.31.146/ptzManager/ptzControl.html"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15, env=env)

        if result.returncode == 0:
            # 读取cookies文件
            try:
                with open('/tmp/cookies.txt', 'r') as f:
                    cookies = f.read()

                print(f"   获取到cookies: {cookies[:100]}...")

                # 解析SessionId
                for line in cookies.split('\n'):
                    if 'session' in line.lower():
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            session_id = parts[6]
                            print(f"   ✅ 从cookie获取SessionId: {session_id}")
                            return session_id

                print("   ❌ 未找到SessionId cookie")
                return None

            except Exception as e:
                print(f"   ❌ 读取cookies失败: {e}")
                return None
        else:
            print(f"   ❌ 请求失败: {result.stderr}")
            return None

    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        return None

def try_known_sessions():
    """尝试已知的SessionId模式"""
    print("🔐 尝试已知SessionId模式...")

    # 常见的SessionId模式
    known_patterns = [
        "1DD2682BD160DCAC9712EA6FC1452D6",
        "D1D66678A96617EF9555E42E67349E2",
        "A1B2C3D4E5F6789012345678901234567",
        "123456789ABCDEF0123456789ABCDEF0"
    ]

    for session_id in known_patterns:
        print(f"   尝试: {session_id[:16]}...")
        if test_session_id(session_id):
            print(f"   ✅ 有效SessionId: {session_id}")
            return session_id

    print("   ❌ 所有已知模式都无效")
    return None

def test_session_id(session_id):
    """测试SessionId是否有效"""
    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "-H", "Accept: application/json",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}',
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                # 检查是否有错误
                if 'error' in response and 'Invailed' in response.get('error', {}).get('message', ''):
                    return False
                return True
            except:
                return True
        return False

    except:
        return False

def create_working_controller(session_id):
    """创建工作的控制器脚本"""
    script_content = f'''#!/usr/bin/env python3
import subprocess, json, time, os

os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'
SESSION_ID = "{session_id}"

def ptz_command(method, params=None):
    if params is None: params = {{"channelid": 0}}
    data = {{"method": method, "param": params}}

    cmd = ["curl", "-s", "--insecure", "--connect-timeout", "5",
           "-H", "Content-Type: application/json",
           "-H", f"SessionId: {{SESSION_ID}}",
           "--data-raw", json.dumps(data),
           "https://192.168.31.146/ipc/grpc_cmd"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except: return False

def up():
    ptz_command("ptz_move_start", {{"channelid": 0, "tiltUp": 120}})
    time.sleep(0.3); ptz_command("ptz_move_stop")

def down():
    ptz_command("ptz_move_start", {{"channelid": 0, "tiltUp": -120}})
    time.sleep(0.3); ptz_command("ptz_move_stop")

def left():
    ptz_command("ptz_move_start", {{"channelid": 0, "panLeft": 120}})
    time.sleep(0.3); ptz_command("ptz_move_stop")

def right():
    ptz_command("ptz_move_start", {{"channelid": 0, "panRight": 120}})
    time.sleep(0.3); ptz_command("ptz_move_stop")

def stop(): ptz_command("ptz_move_stop")

print(f"🎮 PTZ控制器 - SessionId: {session_id[:16]}...")
print("w/s: 上/下, a/d: 左/右, x: 停止, quit: 退出")

while True:
    try:
        cmd = input("命令: ").strip().lower()
        if cmd in ['quit', 'q']: break
        elif cmd == 'w': up()
        elif cmd == 's': down()
        elif cmd == 'a': left()
        elif cmd == 'd': right()
        elif cmd == 'x': stop()
        else: print("未知命令")
    except KeyboardInterrupt: break
'''

    script_file = "/home/fusha/Desktop/vlm_test.py/auto_ptz_controller.py"
    with open(script_file, 'w') as f:
        f.write(script_content)

    os.chmod(script_file, 0o755)
    print(f"✅ 自动控制器已创建: {script_file}")
    return script_file

def main():
    print("🤖 自动获取SessionId工具")
    print("=" * 50)

    # 设置环境
    setup_ssl_compatibility()

    # 获取登录凭据
    print("\n📝 请输入登录信息:")
    username = input("用户名 (默认: admin): ").strip() or "admin"
    password = input("密码 (默认: admin123): ").strip() or "admin123"

    print(f"\n🔍 尝试自动获取SessionId...")
    print(f"   摄像头: 192.168.31.146")
    print(f"   用户名: {username}")

    # 尝试多种登录方法
    login_methods = [
        lambda: try_login_method_1(username, password),
        lambda: try_login_method_2(username, password),
        try_known_sessions
    ]

    session_id = None
    for i, method in enumerate(login_methods, 1):
        print(f"\n🔄 尝试方法 {i}/{len(login_methods)}...")
        session_id = method()
        if session_id:
            break

    if session_id:
        print(f"\n🎉 成功获取SessionId!")
        print(f"   SessionId: {session_id}")

        # 创建工作控制器
        controller_script = create_working_controller(session_id)

        print(f"\n📋 使用方法:")
        print(f"   python {controller_script}")

        # 询问是否立即测试
        test_now = input(f"\n是否立即测试PTZ控制？(Y/n): ").strip().lower()
        if test_now != 'n':
            subprocess.run(['python', controller_script])

    else:
        print(f"\n❌ 自动获取失败")
        print(f"🔄 建议使用手动方式:")
        print(f"   python get_session_manual.py")

if __name__ == "__main__":
    main()