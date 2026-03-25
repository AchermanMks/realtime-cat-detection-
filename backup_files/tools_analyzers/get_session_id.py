#!/usr/bin/env python3
"""
自动获取摄像头SessionId
"""

import requests
import re
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def get_session_id():
    """尝试自动获取SessionId"""
    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin123"

    try:
        # 尝试登录获取SessionId
        login_url = f"https://{camera_ip}/api/login"
        login_data = {
            "username": username,
            "password": password
        }

        session = requests.Session()
        session.verify = False

        print(f"🔐 尝试登录摄像头 {camera_ip}...")

        # 首先获取主页面
        main_response = session.get(f"https://{camera_ip}/", timeout=10)
        print(f"📄 主页面响应: {main_response.status_code}")

        # 查找页面中的SessionId
        if main_response.status_code == 200:
            content = main_response.text

            # 尝试多种SessionId模式
            session_patterns = [
                r'SessionId["\']?\s*[:=]\s*["\']([A-F0-9]+)["\']',
                r'sessionId["\']?\s*[:=]\s*["\']([A-F0-9]+)["\']',
                r'session_id["\']?\s*[:=]\s*["\']([A-F0-9]+)["\']',
                r'["\']([A-F0-9]{32})["\']',  # 32位十六进制
                r'["\']([A-F0-9]{30,40})["\']',  # 30-40位十六进制
            ]

            for pattern in session_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    session_id = matches[0]
                    print(f"✅ 找到SessionId: {session_id}")
                    return session_id

        # 尝试通过登录API获取
        try:
            login_response = session.post(login_url, json=login_data, timeout=10)
            if login_response.status_code == 200:
                # 检查响应头中的SessionId
                for header_name in ['SessionId', 'Set-Cookie', 'X-Session-Id']:
                    if header_name in login_response.headers:
                        header_value = login_response.headers[header_name]
                        session_match = re.search(r'([A-F0-9]{30,40})', header_value)
                        if session_match:
                            session_id = session_match.group(1)
                            print(f"✅ 从响应头获取SessionId: {session_id}")
                            return session_id
        except Exception as e:
            print(f"⚠️ 登录API失败: {e}")

        print("❌ 无法自动获取SessionId")
        print("\n📋 请手动获取:")
        print("1. 打开浏览器访问: https://192.168.31.146")
        print("2. 登录 (admin/admin123)")
        print("3. 打开开发者工具 (F12)")
        print("4. 切换到Network标签")
        print("5. 操作摄像头云台")
        print("6. 查看/ipc/grpc_cmd请求的SessionId头")

        return None

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None

def test_session_id(session_id):
    """测试SessionId是否有效"""
    import subprocess
    import os

    cmd = [
        "curl", "--insecure", "-s",
        "https://192.168.31.146/ipc/grpc_cmd",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}'
    ]

    env = os.environ.copy()
    env.pop('https_proxy', None)
    env.pop('http_proxy', None)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, env=env)
        if result.returncode == 0:
            print(f"✅ SessionId有效!")
            return True
        else:
            print(f"❌ SessionId无效 (返回码: {result.returncode})")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🎯 摄像头SessionId获取工具")
    print("=" * 40)

    session_id = get_session_id()
    if session_id:
        print(f"\n🧪 测试SessionId: {session_id}")
        if test_session_id(session_id):
            print(f"\n🎉 可用的SessionId: {session_id}")
            print("\n📝 请更新脚本中的SessionId值")
        else:
            print(f"\n❌ SessionId无效，请手动获取")