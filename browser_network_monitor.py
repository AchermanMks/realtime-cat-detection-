#!/usr/bin/env python3
"""
浏览器网络监控工具
监控用户在浏览器中的PTZ操作，记录网络请求
"""

import subprocess
import time
import json
import threading
from datetime import datetime
import os

class BrowserNetworkMonitor:
    """浏览器网络监控器"""

    def __init__(self, camera_ip="192.168.31.146"):
        self.camera_ip = camera_ip
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"browser_network_log_{self.timestamp}.txt"
        self.monitoring = False

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def start_tcpdump_monitor(self):
        """启动tcpdump网络监控"""
        pcap_file = f"browser_capture_{self.timestamp}.pcap"

        try:
            cmd = [
                "sudo", "tcpdump",
                "-i", "any",
                "-w", pcap_file,
                f"host {self.camera_ip}"
            ]

            self.log(f"🔍 启动网络抓包: {' '.join(cmd)}")

            process = subprocess.Popen(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

            self.log("✅ 网络抓包已启动")
            return process, pcap_file

        except Exception as e:
            self.log(f"❌ 启动抓包失败: {e}")
            return None, None

    def analyze_pcap_file(self, pcap_file):
        """分析pcap文件"""
        if not os.path.exists(pcap_file):
            self.log("❌ pcap文件不存在")
            return

        try:
            # 使用tshark分析HTTP请求
            cmd = [
                "tshark", "-r", pcap_file,
                "-Y", "http.request or http.response",
                "-T", "fields",
                "-e", "frame.time",
                "-e", "ip.src", "-e", "ip.dst",
                "-e", "http.request.method",
                "-e", "http.request.uri",
                "-e", "http.response.code"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.log("📊 HTTP请求分析:")
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 6:
                            time_str, src, dst, method, uri, code = parts[:6]
                            if method or uri or code:
                                self.log(f"   {time_str}: {src}->{dst} {method} {uri} [{code}]")

        except Exception as e:
            self.log(f"❌ 分析pcap文件失败: {e}")

    def generate_manual_instructions(self):
        """生成手动操作指南"""
        instructions = f"""
🔧 手动PTZ协议分析指南
{'='*50}

📋 步骤1: 浏览器开发者工具设置
1. 打开Chrome浏览器
2. 访问: https://{self.camera_ip}/setting.html
3. 按F12打开开发者工具
4. 切换到 "Network" 标签页
5. 勾选 "Preserve log" 保留日志
6. 清空当前日志 (点击禁止图标)

📋 步骤2: 操作PTZ控制
1. 在摄像头Web界面中找到云台控制
2. 尝试移动云台 (上下左右)
3. 观察Network标签页中的请求

📋 步骤3: 分析网络请求
查找包含以下特征的请求:
- URL包含: ptz, move, control, pan, tilt
- 请求方法: GET, POST, PUT
- 参数包含: direction, speed, action

📋 步骤4: 记录协议信息
对于每个PTZ控制请求记录:
- 请求URL
- 请求方法 (GET/POST)
- 请求参数
- 返回结果

📋 示例 - 可能的PTZ控制模式:

1. GET请求模式:
   /api/ptz?action=move&direction=left&speed=5
   /cgi-bin/ptz.cgi?cmd=start&pan=left&speed=3

2. POST请求模式:
   URL: /api/ptz/control
   Body: {{"action": "move", "direction": "up", "speed": 5}}

3. WebSocket模式:
   连接: ws://{self.camera_ip}/websocket
   消息: {{"type": "ptz", "command": "move_left"}}

📋 常见PTZ参数:
- direction/dir: left, right, up, down
- action: start, stop, move, continuous
- speed: 1-10 或 1-100
- channel: 0, 1 (摄像头通道)
- preset: 1-8 (预置位)

📱 快速测试命令:
curl -k -u admin:admin123 'https://{self.camera_ip}/cgi-bin/ptz.cgi?action=start&code=Left&speed=5'
"""

        instruction_file = f"manual_ptz_guide_{self.timestamp}.txt"
        with open(instruction_file, 'w', encoding='utf-8') as f:
            f.write(instructions)

        self.log(f"📖 操作指南已生成: {instruction_file}")
        print(instructions)

    def run_monitor(self):
        """运行监控"""
        self.log("🚀 启动浏览器网络监控工具")

        # 检查是否有root权限进行抓包
        if os.geteuid() == 0:
            self.log("🔍 检测到root权限，启动网络抓包...")

            process, pcap_file = self.start_tcpdump_monitor()

            if process:
                try:
                    self.log("📱 请在浏览器中访问摄像头并操作PTZ控制")
                    self.log("⏰ 监控60秒，或按Ctrl+C停止...")

                    time.sleep(60)

                    # 停止抓包
                    process.terminate()
                    process.wait()

                    self.log("⏹️ 网络抓包已停止")

                    # 分析结果
                    self.log("📊 分析抓包结果...")
                    self.analyze_pcap_file(pcap_file)

                except KeyboardInterrupt:
                    self.log("⏹️ 用户停止监控")
                    process.terminate()
                    process.wait()
        else:
            self.log("ℹ️ 无root权限，生成手动分析指南...")

        # 生成手动操作指南
        self.generate_manual_instructions()

def main():
    print("🌐 浏览器PTZ网络监控工具")
    print("=" * 50)

    monitor = BrowserNetworkMonitor()

    try:
        monitor.run_monitor()
        print(f"\n📝 详细日志: {monitor.log_file}")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()