#!/usr/bin/env python3
"""
小米摄像头PTZ控制演示脚本
展示基于curl命令逆向工程的完整PTZ控制功能
"""

import time
import sys
import os

# 导入PTZ控制器
from xiaomi_ptz_controller import XiaomiPTZController

def demo_banner():
    """显示演示横幅"""
    print("=" * 80)
    print("🎥 小米摄像头PTZ控制演示")
    print("   基于Web界面curl命令逆向工程实现")
    print("=" * 80)

def demo_basic_movements():
    """演示基本移动功能"""
    print("\n🎯 演示1: 基本方向控制")
    print("-" * 50)

    controller = XiaomiPTZController()

    if not controller.login():
        print("❌ 登录失败，无法继续演示")
        return False

    movements = [
        ("⬆️ 向上", "up"),
        ("⬇️ 向下", "down"),
        ("⬅️ 向左", "left"),
        ("➡️ 向右", "right")
    ]

    print("开始基本移动演示...")
    for name, direction in movements:
        print(f"   {name} 移动中...")
        controller.move_for_duration(direction, speed=80, duration=1.5)
        time.sleep(0.5)

    print("✅ 基本移动演示完成")
    return True

def demo_zoom_control():
    """演示缩放控制"""
    print("\n🔍 演示2: 缩放控制")
    print("-" * 50)

    controller = XiaomiPTZController()

    if not controller.login():
        print("❌ 登录失败")
        return False

    # 缩放演示
    print("   🔍 放大中...")
    controller.zoom_in(100)
    time.sleep(2)
    controller.stop_zoom()

    time.sleep(1)

    print("   🔍 缩小中...")
    controller.zoom_out(100)
    time.sleep(2)
    controller.stop_zoom()

    print("✅ 缩放控制演示完成")
    return True

def demo_preset_positions():
    """演示预设位功能"""
    print("\n📍 演示3: 预设位控制")
    print("-" * 50)

    controller = XiaomiPTZController()

    if not controller.login():
        print("❌ 登录失败")
        return False

    # 移动到不同位置并保存预设
    positions = [
        ("左上角", "left_up", 1),
        ("右上角", "right_up", 2),
        ("左下角", "left_down", 3),
        ("右下角", "right_down", 4)
    ]

    for name, direction, preset_id in positions:
        print(f"   📍 移动到{name}...")
        controller.move_for_duration(direction, speed=100, duration=2)
        time.sleep(0.5)

        print(f"   💾 保存为预设位 {preset_id}")
        controller.save_preset(preset_id)
        time.sleep(1)

    # 测试预设位转到功能
    print("\n   🔄 测试预设位转到功能...")
    for _, _, preset_id in positions:
        print(f"   📍 转到预设位 {preset_id}")
        controller.goto_preset(preset_id)
        time.sleep(2)

    print("✅ 预设位演示完成")
    return True

def demo_api_info():
    """演示API信息获取"""
    print("\n📊 演示4: API信息获取")
    print("-" * 50)

    controller = XiaomiPTZController()

    if not controller.login():
        print("❌ 登录失败")
        return False

    print("   📋 获取PTZ能力信息...")
    controller.get_ptz_ability()

    print("   📋 获取预设位列表...")
    controller.get_ptz_presets()

    print("   📋 获取移动状态...")
    controller.get_move_status()

    print("✅ API信息获取演示完成")
    return True

def demo_continuous_patrol():
    """演示连续巡航"""
    print("\n🔄 演示5: 连续巡航模式")
    print("-" * 50)

    controller = XiaomiPTZController()

    if not controller.login():
        print("❌ 登录失败")
        return False

    print("   🚁 开始巡航模式 (按Ctrl+C停止)...")

    try:
        # 巡航路径：上->右->下->左->循环
        patrol_path = [
            ("⬆️ 上", "up"),
            ("➡️ 右", "right"),
            ("⬇️ 下", "down"),
            ("⬅️ 左", "left")
        ]

        cycles = 0
        while cycles < 2:  # 巡航2圈
            for name, direction in patrol_path:
                print(f"     {name} 巡航...")
                controller.move_for_duration(direction, speed=60, duration=2)
                time.sleep(0.5)

            cycles += 1
            print(f"   ✅ 完成第 {cycles} 圈巡航")

        print("✅ 巡航演示完成")

    except KeyboardInterrupt:
        print("\n   ⏹️ 巡航被用户中断")
        controller.stop_move()

    return True

def interactive_demo_menu():
    """交互式演示菜单"""
    print("\n🎮 交互式演示菜单")
    print("-" * 50)
    print("请选择演示内容:")
    print("  1. 基本移动控制")
    print("  2. 缩放功能")
    print("  3. 预设位管理")
    print("  4. API信息获取")
    print("  5. 连续巡航")
    print("  6. 运行所有演示")
    print("  0. 退出")

    demos = {
        '1': demo_basic_movements,
        '2': demo_zoom_control,
        '3': demo_preset_positions,
        '4': demo_api_info,
        '5': demo_continuous_patrol
    }

    while True:
        try:
            choice = input("\n请选择 (0-6): ").strip()

            if choice == '0':
                print("👋 退出演示")
                break
            elif choice == '6':
                print("\n🚀 运行所有演示...")
                for demo_func in demos.values():
                    if not demo_func():
                        print("❌ 演示失败，停止执行")
                        break
                    time.sleep(2)
                print("\n🎉 所有演示完成！")
            elif choice in demos:
                demos[choice]()
            else:
                print("❌ 无效选择，请输入 0-6")

        except KeyboardInterrupt:
            print("\n👋 用户中断，退出演示")
            break
        except Exception as e:
            print(f"❌ 演示过程中发生错误: {e}")

def show_curl_commands():
    """显示关键curl命令"""
    print("\n📋 关键curl命令参考")
    print("-" * 50)

    commands = [
        ("登录命令", """curl 'https://192.168.31.146/ipc/login' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  --data-raw '{"username":"admin","password":"admin123"}' \\
  --insecure"""),

        ("向上移动", """curl 'https://192.168.31.146/ipc/grpc_cmd' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  -H 'SessionId: YOUR_SESSION_ID' \\
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}' \\
  --insecure"""),

        ("停止移动", """curl 'https://192.168.31.146/ipc/grpc_cmd' \\
  -H 'Content-Type: application/json; charset=UTF-8' \\
  -H 'SessionId: YOUR_SESSION_ID' \\
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}' \\
  --insecure""")
    ]

    for title, cmd in commands:
        print(f"\n🔸 {title}:")
        print(cmd)

def main():
    """主函数"""
    demo_banner()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode == "basic":
            demo_basic_movements()
        elif mode == "zoom":
            demo_zoom_control()
        elif mode == "preset":
            demo_preset_positions()
        elif mode == "info":
            demo_api_info()
        elif mode == "patrol":
            demo_continuous_patrol()
        elif mode == "all":
            demos = [
                demo_basic_movements,
                demo_zoom_control,
                demo_preset_positions,
                demo_api_info,
                demo_continuous_patrol
            ]
            for demo_func in demos:
                if not demo_func():
                    break
                time.sleep(2)
        elif mode == "curl":
            show_curl_commands()
        else:
            print("❌ 未知模式")
            print("使用方法:")
            print("  python demo_ptz_control.py          # 交互式演示")
            print("  python demo_ptz_control.py basic    # 基本移动演示")
            print("  python demo_ptz_control.py zoom     # 缩放演示")
            print("  python demo_ptz_control.py preset   # 预设位演示")
            print("  python demo_ptz_control.py info     # API信息演示")
            print("  python demo_ptz_control.py patrol   # 巡航演示")
            print("  python demo_ptz_control.py all      # 所有演示")
            print("  python demo_ptz_control.py curl     # 显示curl命令")
    else:
        interactive_demo_menu()

if __name__ == "__main__":
    main()