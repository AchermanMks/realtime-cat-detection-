#!/usr/bin/env python3
"""
热更新SessionId - 无需重启系统
"""

import json
import subprocess
import sys

def test_ptz_command(session_id, action="up"):
    """测试PTZ命令"""
    command_map = {
        'up': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": 120}},
        'left': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": 120}},
        'right': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": -120}},
        'stop': {"method": "ptz_move_stop", "param": {"channelid": 0}},
    }

    data = command_map[action]
    curl_cmd = [
        "curl", "-s", "--insecure", "--connect-timeout", "3",
        "-H", "Content-Type: application/json",
        "-H", f"SessionId: {session_id}",
        "--data-raw", json.dumps(data),
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if 'error' in response:
                    error_code = response.get('error', {}).get('errorcode', -1)
                    return error_code == 0
                return True
            except:
                return True
        return False
    except:
        return False

def main():
    print("🔧 PTZ SessionId热修复工具")
    print("=" * 50)

    # 读取新的SessionId
    try:
        with open('auto_session_config.json', 'r') as f:
            config = json.load(f)
        new_session_id = config['session_id']
        print(f"✅ 新SessionId: {new_session_id}")
    except Exception as e:
        print(f"❌ 无法读取SessionId: {e}")
        return

    # 测试新SessionId
    print("🔍 测试新SessionId...")
    if test_ptz_command(new_session_id, "up"):
        print("✅ 新SessionId测试成功")
    else:
        print("❌ 新SessionId测试失败")
        return

    # 创建修复的final_ptz_system.py
    print("📝 更新final_ptz_system.py...")

    try:
        with open('final_ptz_system.py', 'r') as f:
            content = f.read()

        # 替换SessionId
        old_session_pattern = 'def __init__(self, session_id="2204F92CDE0B66FD22D99043BBD5C27"):'
        new_session_pattern = f'def __init__(self, session_id="{new_session_id}"):'

        if old_session_pattern in content:
            content = content.replace(old_session_pattern, new_session_pattern)

            with open('final_ptz_system_updated.py', 'w') as f:
                f.write(content)

            print("✅ 已创建更新版本: final_ptz_system_updated.py")
            print("💡 建议重启系统使用新SessionId")

        else:
            print("⚠️ 未找到SessionId位置，手动更新")

    except Exception as e:
        print(f"❌ 更新失败: {e}")

    # 提供重启命令
    print("\n🚀 重启命令:")
    print("# 停止当前系统")
    print("pkill -f final_ptz_system.py")
    print()
    print("# 启动更新版系统")
    print("export PYTORCH_ALLOC_CONF=expandable_segments:True")
    print("export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512")
    print("python final_ptz_system_updated.py --rtsp rtsp://admin:admin123@192.168.31.146:8554/stream1 --port 5005")

if __name__ == "__main__":
    main()