#!/usr/bin/env python3
"""
强力缩放重置工具
解决摄像头画面无法恢复原始大小的问题
"""

import subprocess
import json
import time
import os

def execute_command(data):
    """执行PTZ命令"""
    os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'

    curl_cmd = [
        "curl", "-s", "--insecure", "--connect-timeout", "5",
        "-H", "Content-Type: application/json",
        "-H", "SessionId: A14CA28A5890F9F378389B37CFF9A46",
        "--data-raw", json.dumps(data),
        "https://192.168.31.146/ipc/grpc_cmd"
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if 'error' in response:
                return response['error']['errorcode'] == 0
        return False
    except Exception as e:
        print(f"命令执行异常: {e}")
        return False

def force_zoom_reset():
    """强力缩放重置序列"""
    print("🎯 开始强力缩放重置序列...")
    print("=" * 50)

    # 5步重置序列
    reset_sequence = [
        ("停止所有PTZ操作", {"method": "ptz_move_stop", "param": {"channelid": 0}}),
        ("大幅缩小", {"method": "ptz_move_start", "param": {"channelid": 0, "zoomOut": 1000}}),
        ("重置到0", {"method": "ptz_move_start", "param": {"channelid": 0, "zoom": 0}}),
        ("设置为1", {"method": "ptz_move_start", "param": {"channelid": 0, "zoom": 1}}),
        ("最终停止", {"method": "ptz_move_stop", "param": {"channelid": 0}})
    ]

    for i, (description, command) in enumerate(reset_sequence):
        print(f"步骤 {i+1}/5: {description}")
        success = execute_command(command)
        print(f"  {'✅ 成功' if success else '❌ 失败'}")
        time.sleep(2)  # 等待2秒让摄像头处理命令

    print("\n🎉 强力重置序列完成!")
    print("📱 请检查摄像头画面是否恢复到原始大小")

def test_zoom_functions():
    """测试完整缩放功能"""
    print("\n🔍 测试完整缩放功能...")

    # 测试放大
    print("1. 测试放大功能:")
    success = execute_command({"method": "ptz_move_start", "param": {"channelid": 0, "zoomIn": 200}})
    print(f"   {'✅ 成功' if success else '❌ 失败'}")

    time.sleep(3)
    print("   (等待3秒观察效果...)")

    # 执行强力重置
    print("\n2. 执行强力重置:")
    force_zoom_reset()

def main():
    print("🎯 强力缩放重置工具")
    print("解决摄像头画面无法恢复原始大小的问题")
    print("=" * 60)

    choice = input("选择操作:\n1. 仅执行强力重置\n2. 完整测试(放大→重置)\n请输入 1 或 2: ").strip()

    if choice == "1":
        force_zoom_reset()
    elif choice == "2":
        test_zoom_functions()
    else:
        print("无效选择，执行强力重置...")
        force_zoom_reset()

if __name__ == "__main__":
    main()