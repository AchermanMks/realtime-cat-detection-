#!/usr/bin/env python3
"""
摄像头监控系统启动器
"""

import os
import sys
import subprocess

def main():
    print("🎥 摄像头智能监控系统")
    print("=" * 40)
    print("请选择启动模式：")
    print("1. 快速测试 (仅显示摄像头)")
    print("2. 完整监控 (AI分析 + GUI)")
    print("3. 高级监控 (Tkinter版本)")
    print("4. 退出")
    print()

    while True:
        try:
            choice = input("请输入选择 (1-4): ").strip()

            if choice == '1':
                print("🚀 启动快速摄像头测试...")
                subprocess.run([sys.executable, "quick_camera_test.py"])
                break
            elif choice == '2':
                print("🚀 启动OpenCV GUI监控系统...")
                subprocess.run([sys.executable, "opencv_gui_monitor.py"])
                break
            elif choice == '3':
                print("🚀 启动高级监控仪表板...")
                if os.path.exists("advanced_monitoring_dashboard.py"):
                    subprocess.run([sys.executable, "advanced_monitoring_dashboard.py"])
                else:
                    print("❌ 高级监控仪表板文件不存在")
                break
            elif choice == '4':
                print("👋 再见!")
                break
            else:
                print("❌ 无效选择，请输入 1-4")
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except EOFError:
            # 非交互环境，默认启动OpenCV监控
            print("🚀 自动启动OpenCV GUI监控系统...")
            subprocess.run([sys.executable, "opencv_gui_monitor.py"])
            break

if __name__ == "__main__":
    main()