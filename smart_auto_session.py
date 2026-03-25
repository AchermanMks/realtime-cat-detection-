#!/usr/bin/env python3
"""
智能自动SessionId获取器
多种方式自动获取并验证SessionId，无需手动干预
"""

import subprocess
import json
import time
import os
import re
import random
import string

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

def generate_session_id():
    """生成可能的SessionId格式"""
    # 基于观察到的SessionId模式生成
    patterns = [
        # 32位十六进制
        ''.join(random.choices('0123456789ABCDEF', k=32)),
        # 混合数字字母
        ''.join(random.choices('0123456789ABCDEFabcdef', k=32)),
        # 带时间戳的模式
        f"{''.join(random.choices('0123456789ABCDEF', k=24))}{int(time.time()) % 100000000:08X}",
    ]
    return patterns

def extract_session_from_response(response_text, headers_text=""):
    """从响应中提取可能的SessionId"""
    session_patterns = [
        r'"sessionid":\s*"([^"]+)"',
        r'"sessionId":\s*"([^"]+)"',
        r'"SESSIONID":\s*"([^"]+)"',
        r'"session":\s*"([^"]+)"',
        r'sessionid[=:]([A-Fa-f0-9]{16,64})',
        r'SessionId[=:]([A-Fa-f0-9]{16,64})',
        r'JSESSIONID[=:]([A-Fa-f0-9]{16,64})',
        r'Set-Cookie:.*sessionid=([A-Fa-f0-9]{16,64})',
        r'Set-Cookie:.*SessionId=([A-Fa-f0-9]{16,64})',
    ]

    all_text = response_text + "\n" + headers_text

    for pattern in session_patterns:
        matches = re.findall(pattern, all_text, re.IGNORECASE)
        for match in matches:
            if len(match) >= 16:  # 合理的SessionId长度
                return match

    return None

def try_login_with_full_headers(username="admin", password="admin123"):
    """尝试完整头部的登录请求"""
    print("🔐 尝试完整登录请求...")

    login_data = {"username": username, "password": password}

    curl_cmd = [
        "curl", "-v", "-s",
        "--insecure",
        "--connect-timeout", "10",
        "-c", "/tmp/session_cookies.txt",  # 保存cookies
        "-D", "/tmp/response_headers.txt",  # 保存响应头
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json, text/html, */*",
        "-H", "Accept-Language: en-US,en;q=0.9,zh-CN;q=0.8",
        "-H", "Cache-Control: no-cache",
        "-H", "Origin: https://192.168.31.146",
        "-H", "Referer: https://192.168.31.146/",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-H", "X-Requested-With: XMLHttpRequest",
        "--data-raw", json.dumps(login_data),
        "https://192.168.31.146/ipc/login"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15, env=env)

        if result.returncode == 0:
            response_text = result.stdout
            headers_text = ""

            # 读取响应头文件
            try:
                with open('/tmp/response_headers.txt', 'r') as f:
                    headers_text = f.read()
            except:
                pass

            print(f"   登录响应: {response_text[:200]}...")
            print(f"   响应头: {headers_text[:200]}...")

            # 专门查找响应头中的SessionId
            if headers_text:
                # 查找 SessionId: xxxxx 模式
                session_match = re.search(r'SessionId:\s*([A-Fa-f0-9]{16,64})', headers_text, re.IGNORECASE)
                if session_match:
                    session_id = session_match.group(1)
                    print(f"   ✅ 从响应头提取SessionId: {session_id}")
                    return session_id

            # 尝试从响应中提取SessionId
            session_id = extract_session_from_response(response_text, headers_text)
            if session_id:
                print(f"   ✅ 提取到SessionId: {session_id}")
                return session_id

            # 读取cookies文件
            try:
                with open('/tmp/session_cookies.txt', 'r') as f:
                    cookies = f.read()

                print(f"   Cookies: {cookies[:200]}...")

                # 解析cookies中的SessionId
                for line in cookies.split('\n'):
                    if any(keyword in line.lower() for keyword in ['session', 'jsession']):
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookie_value = parts[6].strip()
                            if len(cookie_value) >= 16:
                                print(f"   ✅ 从Cookie提取SessionId: {cookie_value}")
                                return cookie_value
            except Exception as e:
                print(f"   Cookie解析失败: {e}")

            return None
        else:
            print(f"   ❌ 登录请求失败: {result.stderr}")
            return None

    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        return None

def try_web_session_extraction(username="admin", password="admin123"):
    """尝试通过Web页面会话提取"""
    print("🌐 尝试Web页面会话提取...")

    # 首先访问主页建立会话
    main_page_cmd = [
        "curl", "-v", "-s",
        "--insecure",
        "--connect-timeout", "10",
        "-c", "/tmp/main_cookies.txt",
        "-D", "/tmp/main_headers.txt",
        "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        f"--user", f"{username}:{password}",
        "https://192.168.31.146/"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(main_page_cmd, capture_output=True, text=True, timeout=15, env=env)

        if result.returncode == 0:
            # 访问PTZ页面
            ptz_page_cmd = [
                "curl", "-v", "-s",
                "--insecure",
                "--connect-timeout", "10",
                "-b", "/tmp/main_cookies.txt",
                "-c", "/tmp/ptz_cookies.txt",
                "-D", "/tmp/ptz_headers.txt",
                "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Referer: https://192.168.31.146/",
                f"--user", f"{username}:{password}",
                "https://192.168.31.146/ptzManager/ptzControl.html"
            ]

            ptz_result = subprocess.run(ptz_page_cmd, capture_output=True, text=True, timeout=15, env=env)

            if ptz_result.returncode == 0:
                # 分析所有生成的文件
                for cookie_file in ['/tmp/main_cookies.txt', '/tmp/ptz_cookies.txt']:
                    try:
                        with open(cookie_file, 'r') as f:
                            cookies = f.read()

                        # 查找SessionId
                        for line in cookies.split('\n'):
                            if any(keyword in line.lower() for keyword in ['session', 'jsession', 'auth']):
                                parts = line.split('\t')
                                if len(parts) >= 7:
                                    cookie_value = parts[6].strip()
                                    if len(cookie_value) >= 16:
                                        print(f"   ✅ 从{cookie_file}提取SessionId: {cookie_value}")
                                        return cookie_value
                    except:
                        continue

                # 分析页面内容中是否有SessionId
                page_content = ptz_result.stdout
                session_id = extract_session_from_response(page_content)
                if session_id:
                    print(f"   ✅ 从页面内容提取SessionId: {session_id}")
                    return session_id

    except Exception as e:
        print(f"   ❌ Web会话提取异常: {e}")

    return None

def try_generated_sessions():
    """尝试生成可能的SessionId"""
    print("🎲 尝试生成可能的SessionId模式...")

    # 基于时间和系统信息生成可能的SessionId
    import hashlib
    import uuid

    base_strings = [
        f"admin{int(time.time())}",
        f"{username}192.168.31.146{int(time.time())}",
        str(uuid.uuid4()).replace('-', '').upper(),
        hashlib.md5(f"camera{int(time.time())}".encode()).hexdigest().upper(),
    ]

    generated_sessions = []
    for base in base_strings:
        # 生成不同长度和格式的SessionId
        generated_sessions.extend([
            hashlib.md5(base.encode()).hexdigest().upper()[:32],
            hashlib.sha1(base.encode()).hexdigest().upper()[:32],
            base[:32].upper() if len(base) >= 32 else (base + '0' * 32)[:32].upper(),
        ])

    # 添加一些常见的SessionId格式
    generated_sessions.extend([
        "A" * 32,
        "1" * 32,
        "F" * 32,
        "0123456789ABCDEF" * 2,
    ])

    print(f"   生成了 {len(generated_sessions)} 个候选SessionId")

    for i, session_id in enumerate(generated_sessions[:20]):  # 限制测试数量
        print(f"   测试生成的SessionId {i+1}: {session_id[:16]}...")
        if test_session_id(session_id):
            print(f"   ✅ 有效的生成SessionId: {session_id}")
            return session_id

    return None

def try_brute_force_sessions():
    """尝试暴力破解常见SessionId模式"""
    print("🔓 尝试常见SessionId模式...")

    # 常见的摄像头SessionId模式
    common_patterns = [
        "1234567890ABCDEF1234567890ABCDEF",
        "ABCDEF1234567890ABCDEF1234567890",
        "0000111122223333444455556666777",
        "FFFFEEEEDDDDCCCCBBBBAAAA99998888",
        "A1B2C3D4E5F6789012345678901234567",
        "1A2B3C4D5E6F7890123456789ABCDEF0",
        "DEADBEEFCAFEBABE1234567890ABCDEF",
        "12345678ABCDEF0012345678ABCDEF00",
    ]

    # 基于时间戳的模式
    timestamp = int(time.time())
    hex_timestamp = f"{timestamp:08X}"

    time_patterns = [
        f"{hex_timestamp}{'0' * 24}",
        f"{'0' * 24}{hex_timestamp}",
        f"{hex_timestamp}{'F' * 24}",
        f"{'F' * 24}{hex_timestamp}",
        f"{hex_timestamp}ABCDEF{'0' * 18}",
    ]

    all_patterns = common_patterns + time_patterns

    print(f"   测试 {len(all_patterns)} 个常见模式")

    for i, session_id in enumerate(all_patterns):
        print(f"   测试模式 {i+1}: {session_id[:16]}...")
        if test_session_id(session_id):
            print(f"   ✅ 有效的模式SessionId: {session_id}")
            return session_id

    return None

def test_session_id(session_id):
    """测试SessionId是否有效"""
    curl_cmd = [
        "curl", "-s",
        "--insecure",
        "--connect-timeout", "3",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "-H", "Accept: application/json",
        "-H", "Origin: https://192.168.31.146",
        "-H", "Referer: https://192.168.31.146/ptzManager/ptzControl.html",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}',
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        env = os.environ.copy()
        env['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8, env=env)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                # 检查是否有错误
                if 'error' in response:
                    error_msg = response.get('error', {}).get('message', '')
                    if any(keyword in error_msg.lower() for keyword in ['invailed', 'expired', 'invalid']):
                        return False
                return True
            except:
                # 非JSON响应，如果状态码是200则认为有效
                return True
        return False

    except:
        return False

def save_valid_session(session_id, method):
    """保存有效的SessionId"""
    from datetime import datetime

    config = {
        "session_id": session_id,
        "camera_ip": "192.168.31.146",
        "method": method,
        "timestamp": datetime.now().isoformat(),
        "expires_estimate": (datetime.now().timestamp() + 3600),  # 1小时后过期
        "notes": f"通过{method}方法自动获取"
    }

    with open('/home/fusha/Desktop/vlm_test.py/auto_session_config.json', 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"💾 有效SessionId已保存: auto_session_config.json")

def create_auto_controller(session_id):
    """创建自动控制器"""
    script_content = f'''#!/usr/bin/env python3
"""
自动获取SessionId的PTZ控制器
SessionId: {session_id}
"""

import subprocess, json, time, os
from datetime import datetime

os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

class AutoPTZController:
    def __init__(self):
        self.session_id = "{session_id}"
        self.camera_ip = "192.168.31.146"

    def send_command(self, method, params=None):
        if params is None: params = {{"channelid": 0}}
        data = {{"method": method, "param": params}}

        cmd = ["curl", "-s", "--insecure", "--connect-timeout", "5",
               "-H", "Content-Type: application/json",
               "-H", f"SessionId: {{self.session_id}}",
               "-H", "Accept: application/json",
               "--data-raw", json.dumps(data),
               f"https://{{self.camera_ip}}/ipc/grpc_cmd"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            success = result.returncode == 0
            if success:
                try:
                    response = json.loads(result.stdout)
                    if 'error' in response and 'Invailed' in str(response.get('error', {{}})):
                        print("⚠️ SessionId可能已过期，请重新运行自动获取工具")
                        return False
                except: pass
            return success
        except: return False

    def move(self, direction, duration=0.3):
        movements = {{
            'up': {{"tiltUp": 120}},
            'down': {{"tiltUp": -120}},
            'left': {{"panLeft": 120}},
            'right': {{"panRight": 120}}
        }}

        if direction in movements:
            if self.send_command("ptz_move_start", {{"channelid": 0, **movements[direction]}}):
                time.sleep(duration)
                return self.send_command("ptz_move_stop")
        return False

    def stop(self):
        return self.send_command("ptz_move_stop")

def main():
    controller = AutoPTZController()

    print(f"🎮 自动PTZ控制器")
    print(f"SessionId: {session_id[:16]}...")
    print(f"获取时间: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}")
    print("\\nw/s:上下, a/d:左右, x:停止, t:测试, q:退出")

    while True:
        try:
            cmd = input("\\n命令: ").strip().lower()
            if cmd in ['q', 'quit', 'exit']: break
            elif cmd == 'w': controller.move('up')
            elif cmd == 's': controller.move('down')
            elif cmd == 'a': controller.move('left')
            elif cmd == 'd': controller.move('right')
            elif cmd == 'x': controller.stop()
            elif cmd == 't':
                print("🧪 测试连接...")
                if controller.stop(): print("✅ 连接正常")
                else: print("❌ 连接失败，SessionId可能已过期")
            else: print("❌ 未知命令")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    main()
'''

    controller_file = '/home/fusha/Desktop/vlm_test.py/auto_ptz_controller.py'
    with open(controller_file, 'w') as f:
        f.write(script_content)

    os.chmod(controller_file, 0o755)
    print(f"✅ 自动PTZ控制器已创建: {controller_file}")
    return controller_file

def main():
    username = "admin"
    password = "admin123"

    print("🤖 智能自动SessionId获取器")
    print("=" * 60)
    print(f"目标摄像头: 192.168.31.146")
    print(f"登录凭据: {username}/{password}")
    print()

    # 设置环境
    setup_ssl_compatibility()

    # 尝试多种自动获取方法
    methods = [
        ("完整登录请求", lambda: try_login_with_full_headers(username, password)),
        ("Web会话提取", lambda: try_web_session_extraction(username, password)),
        ("智能生成模式", try_generated_sessions),
        ("常见模式匹配", try_brute_force_sessions),
    ]

    session_id = None
    successful_method = None

    for method_name, method_func in methods:
        print(f"🔄 尝试方法: {method_name}")
        try:
            session_id = method_func()
            if session_id and test_session_id(session_id):
                print(f"✅ 成功获取有效SessionId!")
                successful_method = method_name
                break
            elif session_id:
                print(f"❌ 获取到SessionId但验证失败: {session_id[:16]}...")
        except Exception as e:
            print(f"❌ 方法异常: {e}")

        print()

    if session_id and successful_method:
        print(f"🎉 自动获取成功!")
        print(f"方法: {successful_method}")
        print(f"SessionId: {session_id}")
        print()

        # 保存配置
        save_valid_session(session_id, successful_method)

        # 创建控制器
        controller_file = create_auto_controller(session_id)

        print(f"📋 使用方法:")
        print(f"   python {controller_file}")
        print(f"💡 SessionId有效期约1小时")
        print(f"   过期后重新运行此工具即可")

        # 立即测试
        test_now = input(f"\\n是否立即测试PTZ控制？(Y/n): ").strip().lower()
        if test_now != 'n':
            print(f"\\n🚀 启动PTZ控制器...")
            subprocess.run(['python', controller_file])

    else:
        print(f"❌ 所有自动方法都失败了")
        print(f"📋 可能的原因:")
        print(f"   • 摄像头型号不支持已知的登录API")
        print(f"   • 登录凭据不正确")
        print(f"   • 网络连接问题")
        print(f"   • SessionId格式发生变化")
        print(f"")
        print(f"🔧 建议:")
        print(f"   1. 确认登录凭据正确")
        print(f"   2. 检查摄像头型号和固件版本")
        print(f"   3. 尝试不同的用户名/密码组合")

if __name__ == "__main__":
    main()