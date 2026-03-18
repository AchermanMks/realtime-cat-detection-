#!/usr/bin/env python3
"""
摄像头云台控制协议抓包分析工具
分析私有协议的PTZ控制命令
"""

import sys
import time
import json
import threading
import subprocess
import requests
from datetime import datetime
from scapy.all import *
from collections import defaultdict
import argparse

class PTZProtocolSniffer:
    """PTZ协议抓包分析器"""

    def __init__(self, camera_ip="192.168.31.146", interface=None):
        self.camera_ip = camera_ip
        self.interface = interface
        self.captured_packets = []
        self.http_sessions = defaultdict(list)
        self.websocket_messages = []
        self.tcp_streams = defaultdict(list)
        self.udp_streams = defaultdict(list)
        self.running = False

        # 创建输出文件
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"ptz_protocol_{self.timestamp}.txt"
        self.pcap_file = f"ptz_capture_{self.timestamp}.pcap"

        print(f"📝 日志文件: {self.log_file}")
        print(f"📦 数据包文件: {self.pcap_file}")

    def log_message(self, message):
        """记录消息到文件和控制台"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def analyze_http_packet(self, packet):
        """分析HTTP数据包"""
        if packet.haslayer(Raw):
            payload = packet[Raw].load.decode('utf-8', errors='ignore')

            # HTTP请求
            if payload.startswith(('GET', 'POST', 'PUT', 'DELETE')):
                lines = payload.split('\r\n')
                method_line = lines[0]

                # 检查是否是云台相关的请求
                ptz_keywords = ['ptz', 'move', 'pan', 'tilt', 'zoom', 'preset', 'control', 'rotate']
                if any(keyword.lower() in method_line.lower() for keyword in ptz_keywords):
                    self.log_message(f"🎮 PTZ HTTP请求: {method_line}")

                    # 记录完整请求
                    self.http_sessions[packet[IP].src].append({
                        'time': time.time(),
                        'method': method_line,
                        'payload': payload[:500] + '...' if len(payload) > 500 else payload
                    })

            # HTTP响应
            elif payload.startswith('HTTP/'):
                if 'ptz' in payload.lower() or 'control' in payload.lower():
                    status_line = payload.split('\r\n')[0]
                    self.log_message(f"🔄 PTZ HTTP响应: {status_line}")

    def analyze_websocket_packet(self, packet):
        """分析WebSocket数据包"""
        if packet.haslayer(Raw):
            payload = packet[Raw].load

            # WebSocket检测（简单的启发式方法）
            if len(payload) > 2:
                # WebSocket frame indicators
                if payload[0] & 0x80:  # FIN bit
                    opcode = payload[0] & 0x0F
                    if opcode in [1, 2]:  # Text or Binary frame
                        try:
                            # 尝试解析WebSocket消息
                            mask_bit = payload[1] & 0x80
                            payload_len = payload[1] & 0x7F

                            if payload_len < 126:
                                start_pos = 2
                                if mask_bit:
                                    start_pos += 4

                                message = payload[start_pos:start_pos+payload_len]
                                message_str = message.decode('utf-8', errors='ignore')

                                # 检查云台相关消息
                                ptz_keywords = ['ptz', 'move', 'pan', 'tilt', 'zoom', 'control']
                                if any(keyword in message_str.lower() for keyword in ptz_keywords):
                                    self.log_message(f"🌐 WebSocket PTZ消息: {message_str[:200]}")
                                    self.websocket_messages.append({
                                        'time': time.time(),
                                        'message': message_str,
                                        'direction': 'unknown'
                                    })
                        except:
                            pass

    def analyze_tcp_stream(self, packet):
        """分析TCP流"""
        if packet.haslayer(TCP) and packet.haslayer(Raw):
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            src_port = packet[TCP].sport
            dst_port = packet[TCP].dport

            # 只分析与摄像头相关的流量
            if src_ip == self.camera_ip or dst_ip == self.camera_ip:
                stream_key = f"{src_ip}:{src_port}->{dst_ip}:{dst_port}"
                payload = packet[Raw].load

                # 检查是否是控制协议
                if len(payload) > 0:
                    # 寻找常见的控制模式
                    hex_payload = payload.hex()

                    # 检查特殊端口或数据模式
                    special_ports = [37777, 34567, 8000, 8080, 554, 8554]
                    if src_port in special_ports or dst_port in special_ports:
                        self.log_message(f"🔌 特殊端口通信 {stream_key}: {hex_payload[:50]}...")

                        self.tcp_streams[stream_key].append({
                            'time': time.time(),
                            'size': len(payload),
                            'hex': hex_payload,
                            'ascii': payload.decode('utf-8', errors='ignore')[:100]
                        })

    def analyze_udp_stream(self, packet):
        """分析UDP流"""
        if packet.haslayer(UDP) and packet.haslayer(Raw):
            src_ip = packet[IP].src
            dst_ip = packet[IP].dst
            src_port = packet[UDP].sport
            dst_port = packet[UDP].dport

            # 只分析与摄像头相关的流量
            if src_ip == self.camera_ip or dst_ip == self.camera_ip:
                stream_key = f"{src_ip}:{src_port}->{dst_ip}:{dst_port}"
                payload = packet[Raw].load
                hex_payload = payload.hex()

                # UDP控制协议检测
                if len(payload) < 100:  # 控制命令通常较短
                    self.log_message(f"📡 UDP通信 {stream_key}: {hex_payload}")

                    self.udp_streams[stream_key].append({
                        'time': time.time(),
                        'size': len(payload),
                        'hex': hex_payload,
                        'ascii': payload.decode('utf-8', errors='ignore')
                    })

    def packet_handler(self, packet):
        """数据包处理器"""
        try:
            # 保存到pcap文件
            wrpcap(self.pcap_file, packet, append=True)

            # 只处理与目标摄像头相关的包
            if packet.haslayer(IP):
                src_ip = packet[IP].src
                dst_ip = packet[IP].dst

                if src_ip == self.camera_ip or dst_ip == self.camera_ip:
                    # 分析不同类型的包
                    if packet.haslayer(TCP):
                        if packet[TCP].dport == 80 or packet[TCP].sport == 80:
                            self.analyze_http_packet(packet)
                        elif packet[TCP].dport == 8080 or packet[TCP].sport == 8080:
                            self.analyze_websocket_packet(packet)
                        else:
                            self.analyze_tcp_stream(packet)

                    elif packet.haslayer(UDP):
                        self.analyze_udp_stream(packet)

        except Exception as e:
            pass  # 忽略解析错误

    def start_capture(self, duration=None):
        """开始抓包"""
        self.running = True
        self.log_message(f"🔍 开始抓包，目标: {self.camera_ip}")
        self.log_message(f"📡 网络接口: {self.interface or '自动检测'}")

        # 设置过滤器，只捕获与摄像头相关的流量
        filter_str = f"host {self.camera_ip}"

        try:
            if duration:
                self.log_message(f"⏰ 抓包时长: {duration}秒")
                sniff(iface=self.interface, filter=filter_str,
                      prn=self.packet_handler, timeout=duration)
            else:
                self.log_message("⏰ 持续抓包，按Ctrl+C停止")
                sniff(iface=self.interface, filter=filter_str,
                      prn=self.packet_handler)

        except KeyboardInterrupt:
            self.log_message("⏹️  用户停止抓包")
        except Exception as e:
            self.log_message(f"❌ 抓包错误: {e}")

        finally:
            self.running = False
            self.generate_report()

    def test_ptz_web_interface(self):
        """测试Web界面的PTZ控制"""
        self.log_message("🌐 测试Web界面PTZ控制...")

        # 常见的PTZ控制URL
        base_url = f"https://{self.camera_ip}"
        test_urls = [
            "/setting.html",
            "/cgi-bin/ptz.cgi",
            "/api/ptz",
            "/control/ptz",
            "/web/cgi-bin/hi3510/ptzctrl.cgi",
        ]

        session = requests.Session()
        session.verify = False  # 忽略SSL证书

        for url in test_urls:
            try:
                full_url = base_url + url
                self.log_message(f"🔗 测试URL: {full_url}")

                response = session.get(full_url, timeout=5, auth=('admin', 'admin123'))
                self.log_message(f"   状态码: {response.status_code}")

                if response.status_code == 200:
                    # 检查响应中的PTZ相关内容
                    content = response.text.lower()
                    ptz_keywords = ['ptz', 'pan', 'tilt', 'zoom', 'move', 'preset', 'control']
                    found_keywords = [kw for kw in ptz_keywords if kw in content]

                    if found_keywords:
                        self.log_message(f"   📍 发现PTZ关键词: {found_keywords}")

                        # 保存页面内容
                        filename = f"ptz_page_{url.replace('/', '_')}_{self.timestamp}.html"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        self.log_message(f"   💾 页面已保存: {filename}")

            except Exception as e:
                self.log_message(f"   ❌ 测试失败: {e}")

    def generate_report(self):
        """生成分析报告"""
        self.log_message("📊 生成分析报告...")

        report_file = f"ptz_analysis_report_{self.timestamp}.txt"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + '\n')
            f.write("PTZ协议分析报告\n")
            f.write("=" * 60 + '\n')
            f.write(f"摄像头IP: {self.camera_ip}\n")
            f.write(f"分析时间: {datetime.now()}\n\n")

            # HTTP会话分析
            if self.http_sessions:
                f.write("🌐 HTTP PTZ请求:\n")
                f.write("-" * 40 + '\n')
                for ip, sessions in self.http_sessions.items():
                    f.write(f"来源IP: {ip}\n")
                    for session in sessions:
                        f.write(f"  时间: {datetime.fromtimestamp(session['time'])}\n")
                        f.write(f"  请求: {session['method']}\n")
                        f.write(f"  内容: {session['payload'][:200]}...\n\n")

            # WebSocket消息分析
            if self.websocket_messages:
                f.write("🌐 WebSocket PTZ消息:\n")
                f.write("-" * 40 + '\n')
                for msg in self.websocket_messages:
                    f.write(f"时间: {datetime.fromtimestamp(msg['time'])}\n")
                    f.write(f"消息: {msg['message']}\n\n")

            # TCP流分析
            if self.tcp_streams:
                f.write("🔌 TCP流分析:\n")
                f.write("-" * 40 + '\n')
                for stream, packets in self.tcp_streams.items():
                    f.write(f"流: {stream}\n")
                    f.write(f"数据包数量: {len(packets)}\n")
                    for i, pkt in enumerate(packets[:5]):  # 只显示前5个
                        f.write(f"  包{i+1}: {pkt['hex'][:50]}... ({pkt['size']}字节)\n")
                        if pkt['ascii'].strip():
                            f.write(f"       ASCII: {pkt['ascii'][:50]}...\n")
                    f.write('\n')

            # UDP流分析
            if self.udp_streams:
                f.write("📡 UDP流分析:\n")
                f.write("-" * 40 + '\n')
                for stream, packets in self.udp_streams.items():
                    f.write(f"流: {stream}\n")
                    f.write(f"数据包数量: {len(packets)}\n")
                    for i, pkt in enumerate(packets):
                        f.write(f"  包{i+1}: {pkt['hex']} ({pkt['size']}字节)\n")
                        if pkt['ascii'].strip():
                            f.write(f"        ASCII: {pkt['ascii']}\n")
                    f.write('\n')

            # 总结
            f.write("📋 分析总结:\n")
            f.write("-" * 40 + '\n')
            f.write(f"HTTP PTZ会话: {len(self.http_sessions)}\n")
            f.write(f"WebSocket消息: {len(self.websocket_messages)}\n")
            f.write(f"TCP流: {len(self.tcp_streams)}\n")
            f.write(f"UDP流: {len(self.udp_streams)}\n")

        self.log_message(f"📄 报告已生成: {report_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PTZ协议抓包分析工具')
    parser.add_argument('--ip', default='192.168.31.146', help='摄像头IP地址')
    parser.add_argument('--interface', help='网络接口名称')
    parser.add_argument('--duration', type=int, help='抓包时长（秒）')
    parser.add_argument('--test-web', action='store_true', help='测试Web界面')

    args = parser.parse_args()

    # 检查权限
    if os.geteuid() != 0:
        print("❌ 需要root权限运行抓包功能")
        print("请使用: sudo python3 ptz_protocol_sniffer.py")
        return

    print("🔍 PTZ协议抓包分析工具")
    print("=" * 50)

    sniffer = PTZProtocolSniffer(camera_ip=args.ip, interface=args.interface)

    try:
        # 测试Web界面
        if args.test_web:
            sniffer.test_ptz_web_interface()

        # 开始抓包
        print("\n📡 准备开始抓包...")
        print("💡 操作摄像头的PTZ控制，然后观察抓包结果")
        print("🎮 建议操作：在Web界面中控制云台移动、缩放等")

        input("按Enter键开始抓包...")

        sniffer.start_capture(duration=args.duration)

    except KeyboardInterrupt:
        print("\n⏹️  用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()