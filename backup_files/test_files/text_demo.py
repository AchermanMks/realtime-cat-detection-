#!/usr/bin/env python3
"""
文本版监控演示
展示监控系统的核心功能和数据流
"""

import time
import random
import json
from datetime import datetime
import threading
import queue

class TextMonitoringDemo:
    """文本版监控演示"""

    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.analysis_count = 0
        self.alert_count = 0
        self.start_time = time.time()

        # 模拟场景
        self.scenarios = [
            {
                "name": "办公室环境",
                "objects": ["桌子", "椅子", "电脑", "文件", "植物"],
                "persons": 2,
                "activities": ["工作", "开会", "讨论"],
                "risk_level": "低",
                "anomalies": []
            },
            {
                "name": "停车场",
                "objects": ["汽车", "路灯", "标识牌", "栅栏"],
                "persons": 1,
                "activities": ["停车", "走路"],
                "risk_level": "低",
                "anomalies": []
            },
            {
                "name": "工厂车间",
                "objects": ["机器设备", "工具", "原材料", "安全标识"],
                "persons": 3,
                "activities": ["操作机器", "检查质量", "搬运"],
                "risk_level": "中",
                "anomalies": ["未戴安全帽"]
            },
            {
                "name": "仓库",
                "objects": ["货架", "箱子", "叉车", "扫描设备"],
                "persons": 2,
                "activities": ["搬运货物", "清点库存"],
                "risk_level": "高",
                "anomalies": ["危险物品标识不清", "通道堵塞"]
            },
            {
                "name": "实验室",
                "objects": ["实验台", "化学品", "仪器设备", "通风橱"],
                "persons": 1,
                "activities": ["进行实验", "记录数据"],
                "risk_level": "高",
                "anomalies": ["化学品泄漏风险", "防护设备不当"]
            }
        ]
        self.current_scenario = 0

    def print_header(self, title):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"🎥 {title}")
        print(f"{'='*60}")

    def print_status_bar(self):
        """打印状态栏"""
        uptime = time.time() - self.start_time
        fps = self.frame_count / max(uptime, 1)

        status = f"运行时间: {uptime:.0f}s | 帧数: {self.frame_count} | FPS: {fps:.1f} | 分析: {self.analysis_count} | 报警: {self.alert_count}"
        print(f"\n📊 {status}")
        print("-" * 60)

    def generate_frame_info(self):
        """生成帧信息"""
        self.frame_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        print(f"📹 [{timestamp}] 帧 #{self.frame_count:05d} | 分辨率: 640x480 | 格式: BGR")

    def simulate_vlm_analysis(self):
        """模拟VLM分析"""
        scenario = self.scenarios[self.current_scenario]
        analysis_time = random.uniform(1.5, 4.0)

        print(f"\n🤖 开始AI视觉分析...")
        print(f"   ⏳ 模型推理中... ({analysis_time:.1f}秒)")
        time.sleep(min(analysis_time, 2.0))  # 限制演示时间

        self.analysis_count += 1

        # 生成分析结果
        result = {
            "timestamp": time.time(),
            "scene": scenario["name"],
            "objects_detected": random.sample(scenario["objects"], min(3, len(scenario["objects"]))),
            "person_count": scenario["persons"] + random.randint(-1, 1),
            "activities": random.sample(scenario["activities"], min(2, len(scenario["activities"]))),
            "risk_level": scenario["risk_level"],
            "anomalies": scenario["anomalies"],
            "confidence": random.uniform(0.75, 0.95),
            "analysis_time": analysis_time
        }

        self.display_analysis_result(result)

        # 检查是否需要报警
        if result["risk_level"] in ["中", "高"] or result["anomalies"]:
            self.trigger_alert(result)

        return result

    def display_analysis_result(self, result):
        """显示分析结果"""
        print(f"\n🎯 AI分析结果 #{self.analysis_count}")
        print(f"   🎬 场景: {result['scene']}")
        print(f"   📦 检测物体: {', '.join(result['objects_detected'])}")
        print(f"   👥 人员数量: {result['person_count']}人")
        print(f"   🏃 活动状态: {', '.join(result['activities'])}")
        print(f"   🎯 置信度: {result['confidence']:.1%}")
        print(f"   🚨 风险级别: {result['risk_level']}")

        if result['anomalies']:
            print(f"   ⚠️ 异常检测:")
            for anomaly in result['anomalies']:
                print(f"      • {anomaly}")

        print(f"   ⏱️ 分析耗时: {result['analysis_time']:.2f}秒")

    def trigger_alert(self, result):
        """触发报警"""
        self.alert_count += 1
        alert_time = datetime.now().strftime("%H:%M:%S")

        print(f"\n🚨 报警 #{self.alert_count:03d} - {alert_time}")
        print(f"   📍 位置: {result['scene']}")
        print(f"   🔥 风险级别: {result['risk_level']}")

        if result['anomalies']:
            print(f"   ⚠️ 异常情况:")
            for anomaly in result['anomalies']:
                print(f"      • {anomaly}")

        print(f"   💡 建议: 立即检查现场情况")

    def switch_scenario(self):
        """切换场景"""
        self.current_scenario = (self.current_scenario + 1) % len(self.scenarios)
        scenario = self.scenarios[self.current_scenario]
        print(f"\n🔄 场景切换: {scenario['name']}")
        print(f"   预期风险级别: {scenario['risk_level']}")

    def run_demo(self):
        """运行演示"""
        self.print_header("实时监控分析系统演示")

        print("🎬 欢迎使用实时监控分析系统！")
        print("\n📋 系统功能:")
        print("   • 实时视频流处理")
        print("   • AI视觉分析 (VLM模型)")
        print("   • 智能风险评估")
        print("   • 异常检测与报警")
        print("   • 多场景监控")

        print(f"\n🎯 演示配置:")
        print(f"   • 视频帧率: 15 FPS")
        print(f"   • AI分析间隔: 每5秒")
        print(f"   • 场景数量: {len(self.scenarios)}个")
        print(f"   • 演示时长: 60秒")

        input("\n按回车键开始演示...")

        self.running = True
        self.start_time = time.time()
        last_analysis_time = 0
        last_scenario_switch = 0
        frame_interval = 1.0 / 15  # 15 FPS
        analysis_interval = 5.0    # 每5秒分析一次
        scenario_switch_interval = 15.0  # 每15秒切换场景

        demo_duration = 60  # 演示60秒

        try:
            while self.running and (time.time() - self.start_time) < demo_duration:
                current_time = time.time()

                # 生成视频帧
                self.generate_frame_info()

                # AI分析
                if current_time - last_analysis_time >= analysis_interval:
                    self.simulate_vlm_analysis()
                    last_analysis_time = current_time

                # 场景切换
                if current_time - last_scenario_switch >= scenario_switch_interval:
                    self.switch_scenario()
                    last_scenario_switch = current_time

                # 显示状态
                self.print_status_bar()

                # 控制帧率
                time.sleep(frame_interval)

        except KeyboardInterrupt:
            print("\n⚠️ 演示被用户中断")

        self.running = False
        self.print_final_stats()

    def print_final_stats(self):
        """打印最终统计"""
        self.print_header("演示完成 - 统计报告")

        total_time = time.time() - self.start_time
        avg_fps = self.frame_count / total_time

        print(f"📈 性能统计:")
        print(f"   • 总运行时间: {total_time:.1f}秒")
        print(f"   • 总帧数: {self.frame_count}")
        print(f"   • 平均FPS: {avg_fps:.1f}")
        print(f"   • AI分析次数: {self.analysis_count}")
        print(f"   • 触发报警次数: {self.alert_count}")

        print(f"\n🎯 系统效率:")
        if self.analysis_count > 0:
            analysis_rate = total_time / self.analysis_count
            print(f"   • 分析频率: 每{analysis_rate:.1f}秒一次")

        alert_rate = (self.alert_count / max(self.analysis_count, 1)) * 100
        print(f"   • 报警率: {alert_rate:.1f}%")

        print(f"\n🏆 演示结论:")
        print(f"   • ✅ 系统运行稳定")
        print(f"   • ✅ AI分析功能正常")
        print(f"   • ✅ 报警机制有效")
        print(f"   • ✅ 多场景支持完整")

        print(f"\n💡 实际部署建议:")
        print(f"   • 使用GPU加速提升分析速度")
        print(f"   • 根据场景调整分析间隔")
        print(f"   • 配置适当的报警阈值")
        print(f"   • 定期备份监控数据")

def main():
    """主函数"""
    demo = TextMonitoringDemo()
    demo.run_demo()

if __name__ == "__main__":
    main()