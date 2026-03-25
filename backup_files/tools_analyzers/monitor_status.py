#!/usr/bin/env python3
"""
监控系统状态显示
实时显示监控系统的运行状态
"""

import time
import random
import os
import sys
from datetime import datetime

def clear_screen():
    """清屏"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    """打印标题"""
    print("🎥 实时监控及分析系统 - 状态面板")
    print("=" * 60)

def print_system_info():
    """打印系统信息"""
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 系统平台: {sys.platform}")
    print(f"🐍 Python版本: {sys.version.split()[0]}")
    print()

def simulate_monitoring_status():
    """模拟监控状态"""
    start_time = time.time()
    frame_count = 0
    analysis_count = 0
    alert_count = 0

    # 模拟场景
    scenarios = [
        {"name": "办公室环境", "risk": "🟢 低", "activity": "正常办公"},
        {"name": "实验室", "risk": "🟡 中", "activity": "实验进行中"},
        {"name": "生产车间", "risk": "🔴 高", "activity": "设备运行"},
        {"name": "停车场", "risk": "🟢 低", "activity": "车辆进出"},
        {"name": "仓库", "risk": "🟡 中", "activity": "货物搬运"}
    ]

    try:
        while True:
            clear_screen()
            print_header()
            print_system_info()

            # 模拟数据更新
            frame_count += random.randint(12, 18)  # 模拟FPS
            if random.random() < 0.3:  # 30%概率进行分析
                analysis_count += 1
            if random.random() < 0.1:  # 10%概率触发报警
                alert_count += 1

            # 当前状态
            current_scenario = random.choice(scenarios)
            uptime = time.time() - start_time

            print("📊 系统状态:")
            print("-" * 40)
            print(f"🕐 运行时间: {int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}")
            print(f"📹 处理帧数: {frame_count:,}")
            print(f"📊 平均FPS: {frame_count/max(uptime, 1):.1f}")
            print(f"🤖 AI分析次数: {analysis_count}")
            print(f"⚠️  报警次数: {alert_count}")
            print()

            print("🎬 当前监控场景:")
            print("-" * 40)
            print(f"📍 场景: {current_scenario['name']}")
            print(f"🚨 风险级别: {current_scenario['risk']}")
            print(f"🏃 活动状态: {current_scenario['activity']}")
            print()

            # 模拟检测到的对象
            objects = ["人员", "车辆", "设备", "物品", "标识"]
            detected = random.sample(objects, random.randint(2, 4))
            print(f"📦 检测到的对象: {', '.join(detected)}")
            print()

            # 系统组件状态
            print("🔧 系统组件状态:")
            print("-" * 40)
            components = [
                ("摄像头连接", "✅ 正常", "2304x1296@40fps"),
                ("AI模型", "✅ 就绪", "Qwen2-VL-7B"),
                ("数据库", "✅ 运行", "SQLite"),
                ("Web服务", "🔄 启动中", "端口5000"),
                ("报警系统", "✅ 监听", "实时检测"),
            ]

            for name, status, info in components:
                print(f"{name:12} {status:8} {info}")
            print()

            # 最新活动
            print("📋 最新活动:")
            print("-" * 40)
            activities = [
                f"🔍 AI分析完成 - {current_scenario['name']}",
                f"📹 处理视频帧 - {random.randint(1000,9999)}",
                f"💾 保存分析数据",
                f"🔔 系统健康检查",
            ]

            for i, activity in enumerate(activities[:3]):
                timestamp = (datetime.now().timestamp() - i*30)
                time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                print(f"[{time_str}] {activity}")
            print()

            print("🌐 访问方式:")
            print("-" * 40)
            print("• Web界面: http://localhost:5000 (启动中)")
            print("• 命令行: python3 cli_launcher.py")
            print("• 文本演示: python3 auto_demo.py")
            print()
            print("💡 按 Ctrl+C 退出状态显示")

            time.sleep(2)  # 每2秒刷新

    except KeyboardInterrupt:
        clear_screen()
        print("👋 监控状态显示已退出")

def main():
    print("🚀 启动监控系统状态显示...")
    time.sleep(1)
    simulate_monitoring_status()

if __name__ == "__main__":
    main()