#!/usr/bin/env python3
"""
自动演示监控系统
展示完整的监控分析流程
"""

import time
import random
import json
from datetime import datetime

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🎥 {title}")
    print(f"{'='*60}")

def simulate_monitoring_system():
    """模拟监控系统运行"""
    print_header("实时监控分析系统 - 自动演示")

    print("🚀 系统启动中...")
    print("📡 连接摄像头... ✅")
    print("🤖 加载AI模型... ✅")
    print("💾 初始化数据库... ✅")
    print("🔔 启动报警系统... ✅")

    # 模拟场景
    scenarios = [
        {
            "name": "办公室环境",
            "description": "日常办公区域监控",
            "objects": ["桌子", "椅子", "电脑", "文件柜", "植物"],
            "persons": 2,
            "activities": ["编程工作", "视频会议", "文档整理"],
            "risk_level": "低",
            "anomalies": [],
            "color": "🟢"
        },
        {
            "name": "实验室环境",
            "description": "科研实验室监控",
            "objects": ["实验台", "显微镜", "化学试剂", "防护设备"],
            "persons": 1,
            "activities": ["进行实验", "数据记录", "样本处理"],
            "risk_level": "中",
            "anomalies": ["防护用品佩戴不当"],
            "color": "🟡"
        },
        {
            "name": "工厂车间",
            "description": "生产车间安全监控",
            "objects": ["生产设备", "传送带", "安全标识", "工具箱"],
            "persons": 3,
            "activities": ["设备操作", "质量检查", "设备维护"],
            "risk_level": "高",
            "anomalies": ["未佩戴安全帽", "危险区域闯入"],
            "color": "🔴"
        }
    ]

    frame_count = 0
    analysis_count = 0
    alert_count = 0
    start_time = time.time()

    print("\n🎬 开始实时监控演示...")

    for cycle in range(3):  # 演示3个完整周期
        for scenario_idx, scenario in enumerate(scenarios):
            print(f"\n🔄 切换场景: {scenario['name']}")
            print(f"📝 {scenario['description']}")
            print(f"🎯 预期风险级别: {scenario['color']} {scenario['risk_level']}")

            # 模拟5秒的视频流
            for second in range(5):
                # 模拟视频帧
                for frame in range(15):  # 15 FPS
                    frame_count += 1
                    if frame_count % 45 == 0:  # 每3秒显示一次帧信息
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        print(f"📹 [{timestamp}] 处理帧 #{frame_count:05d}")

                # AI分析
                if second % 2 == 0:  # 每2秒分析一次
                    analysis_count += 1
                    analysis_time = random.uniform(1.2, 2.8)

                    print(f"\n🤖 AI分析 #{analysis_count:02d}")
                    print(f"   ⏳ VLM模型推理中... ({analysis_time:.1f}s)")

                    # 模拟分析结果
                    detected_objects = random.sample(scenario["objects"], min(3, len(scenario["objects"])))
                    person_count = scenario["persons"] + random.randint(-1, 1)
                    confidence = random.uniform(0.82, 0.96)

                    print(f"   🎬 场景识别: {scenario['name']}")
                    print(f"   📦 检测物体: {', '.join(detected_objects)}")
                    print(f"   👥 人员统计: {max(0, person_count)}人")
                    print(f"   🎯 识别置信度: {confidence:.1%}")
                    print(f"   🚨 风险评估: {scenario['color']} {scenario['risk_level']}风险")

                    # 活动识别
                    activities = random.sample(scenario["activities"], min(2, len(scenario["activities"])))
                    print(f"   🏃 活动识别: {', '.join(activities)}")

                    # 异常检测
                    if scenario["anomalies"]:
                        if random.random() > 0.5:  # 50%概率检测到异常
                            detected_anomaly = random.choice(scenario["anomalies"])
                            print(f"   ⚠️ 异常检测: {detected_anomaly}")

                            # 触发报警
                            alert_count += 1
                            alert_time = datetime.now().strftime("%H:%M:%S")
                            print(f"\n🚨 报警 #{alert_count:03d} - {alert_time}")
                            print(f"   📍 位置: {scenario['name']}")
                            print(f"   🔥 风险类型: {detected_anomaly}")
                            print(f"   💡 处理建议: 立即派遣安全人员检查")
                            print(f"   📸 证据保存: 自动截图并存档")

                time.sleep(0.8)  # 控制演示速度

    # 最终统计
    total_time = time.time() - start_time
    avg_fps = frame_count / total_time

    print_header("演示完成 - 系统报告")

    print(f"📊 运行统计:")
    print(f"   • 运行时长: {total_time:.1f}秒")
    print(f"   • 处理帧数: {frame_count:,}帧")
    print(f"   • 平均帧率: {avg_fps:.1f} FPS")
    print(f"   • AI分析次数: {analysis_count}次")
    print(f"   • 触发报警: {alert_count}次")

    alert_rate = (alert_count / max(analysis_count, 1)) * 100
    print(f"   • 报警率: {alert_rate:.1f}%")

    print(f"\n🎯 系统能力展示:")
    print(f"   ✅ 多场景实时监控")
    print(f"   ✅ AI智能分析识别")
    print(f"   ✅ 异常自动检测")
    print(f"   ✅ 智能风险评估")
    print(f"   ✅ 实时报警机制")
    print(f"   ✅ 数据统计分析")

    print(f"\n🚀 技术特色:")
    print(f"   • 基于VLM(视觉语言模型)的智能分析")
    print(f"   • 多线程并行处理架构")
    print(f"   • 实时风险评估算法")
    print(f"   • 自适应场景识别")
    print(f"   • 历史数据持久化存储")

    print(f"\n💼 应用场景:")
    print(f"   🏢 办公楼宇安全监控")
    print(f"   🏭 工厂生产安全管理")
    print(f"   🔬 实验室安全监督")
    print(f"   🏪 商业场所客流分析")
    print(f"   🚗 停车场车辆管理")
    print(f"   🏥 医院区域安全监控")

    print_header("演示结束 - 感谢观看")
    print("🎉 实时监控及分析系统演示完成！")
    print("📞 如需了解更多信息或定制化部署，请联系技术团队。")

def main():
    """主函数"""
    simulate_monitoring_system()

if __name__ == "__main__":
    main()