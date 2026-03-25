#!/usr/bin/env python3
"""
SessionId获取助手
帮助获取摄像头有效的会话ID
"""

import requests
import json
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_session_info():
    """获取会话信息的指导"""
    print("🔑 获取摄像头SessionId指导")
    print("=" * 50)
    print()
    print("📋 步骤说明:")
    print("1. 打开浏览器，访问摄像头Web界面: https://192.168.31.146")
    print("2. 登录到摄像头管理界面")
    print("3. 导航到PTZ控制页面")
    print("4. 按F12打开开发者工具")
    print("5. 点击Network(网络)标签")
    print("6. 执行一次PTZ操作（如点击上下左右按钮）")
    print("7. 在网络请求中找到 '/ipc/grpc_cmd' 请求")
    print("8. 查看请求头中的 'SessionId' 值")
    print()
    print("💡 或者直接在浏览器console运行:")
    print("document.cookie.split(';').find(c => c.includes('SessionId'))")
    print()
    print("🔧 获取SessionId后，修改 direct_ptz_controller.py 中的 session_id 参数")

def test_connection(camera_ip="192.168.31.146"):
    """测试摄像头连接"""
    print(f"\n🔍 测试摄像头连接: {camera_ip}")
    print("-" * 30)

    # 测试基本连接
    try:
        response = requests.get(
            f"https://{camera_ip}",
            verify=False,
            timeout=5
        )
        print(f"✅ 摄像头可访问: HTTP {response.status_code}")
        return True
    except requests.exceptions.SSLError:
        print("⚠️ SSL连接问题，但摄像头可能仍然可访问")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到摄像头")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False

def create_test_script():
    """创建测试脚本"""
    test_script = '''#!/bin/bash
# 测试PTZ控制的简化脚本
# 使用之前请更新SessionId

CAMERA_IP="192.168.31.146"
SESSION_ID="请在这里填入您的SessionId"

echo "🎮 测试PTZ控制"
echo "使用SessionId: $SESSION_ID"

# 测试停止命令
curl "https://$CAMERA_IP/ipc/grpc_cmd" \\
  -H "Content-Type: application/json" \\
  -H "SessionId: $SESSION_ID" \\
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}' \\
  --insecure -s | jq .

echo "如果返回成功的JSON响应，说明SessionId有效"
'''

    with open('/home/fusha/Desktop/vlm_test.py/test_ptz.sh', 'w') as f:
        f.write(test_script)

    print("\n📝 已创建测试脚本: test_ptz.sh")
    print("请编辑脚本中的SessionId，然后运行: bash test_ptz.sh")

if __name__ == "__main__":
    get_session_info()
    test_connection()
    create_test_script()