#!/usr/bin/env python3
"""
gRPC PTZ控制协议分析工具
基于发现的 /ipc/grpc_cmd 端点
"""

import requests
import json
import base64
import time
from datetime import datetime
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GrpcPTZAnalyzer:
    """gRPC PTZ分析器"""

    def __init__(self, camera_ip="192.168.31.146", username="admin", password="admin123"):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password
        self.base_url = f"https://{camera_ip}"
        self.grpc_endpoint = "/ipc/grpc_cmd"

        self.session = requests.Session()
        self.session.verify = False

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"grpc_ptz_analysis_{self.timestamp}.txt"

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

    def create_extraction_guide(self):
        """创建详细的提取指南"""

        guide = f"""
🔍 gRPC PTZ请求详细信息提取指南
==========================================

✅ 已发现PTZ控制端点: https://192.168.31.146/ipc/grpc_cmd

📋 现在需要获取更多详细信息，请在浏览器开发者工具中：

## 1. 点击该请求 (/ipc/grpc_cmd)

## 2. 查看 Headers 标签页，提供：
### Request Headers:
- Content-Type: [通常是 application/grpc-web+proto 或 application/x-protobuf]
- Authorization: [认证信息]
- Content-Length: [内容长度]
- User-Agent: [浏览器信息]

## 3. 查看 Payload 标签页，提供：
### Request Payload:
[这里会显示发送给服务器的数据，可能是二进制或Base64编码]

## 4. 查看 Response 标签页，提供：
### Response Headers:
- Content-Type:
- Content-Length:

### Response Body:
[服务器返回的内容]

## 5. 操作不同方向，分别记录：
- 向左移动的完整请求
- 向右移动的完整请求
- 向上移动的完整请求
- 向下移动的完整请求

## 📋 信息收集模板：

=== PTZ操作: 向左移动 ===
URL: https://192.168.31.146/ipc/grpc_cmd
方法: POST

Request Headers:
Content-Type:
Authorization:
User-Agent:
Content-Length:

Request Payload (原始内容):
[粘贴Payload标签页中的内容]

Response:
[粘贴Response内容]

=== PTZ操作: 向右移动 ===
[同样的信息...]

## 💡 特别提示：

1. gRPC通常使用二进制格式，Payload可能显示为：
   - 十六进制数据
   - Base64编码
   - 或乱码字符

2. 如果可以复制为cURL命令更好：
   右键请求 -> Copy as cURL (bash)

3. 注意观察不同方向的Payload是否有差异
"""

        guide_file = f"gRPC_详细提取指南_{self.timestamp}.txt"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide)

        self.log(f"📖 详细提取指南已生成: {guide_file}")
        print(guide)

        return guide_file

    def analyze_grpc_patterns(self):
        """分析可能的gRPC模式"""

        self.log("🔍 分析gRPC PTZ可能的协议模式...")

        patterns = {
            "Protocol Buffers": "二进制编码的结构化数据",
            "JSON over gRPC": "JSON格式包装在gRPC中",
            "Base64 Encoded": "Base64编码的二进制数据",
            "Custom Binary": "厂商自定义的二进制协议"
        }

        for pattern, desc in patterns.items():
            self.log(f"   📋 {pattern}: {desc}")

    def generate_test_payloads(self):
        """生成测试用的gRPC Payload"""

        self.log("🧪 生成可能的gRPC测试Payload...")

        # 常见的PTZ命令结构
        test_payloads = [
            # JSON格式
            {
                "type": "JSON",
                "examples": [
                    '{"command": "ptz", "action": "move", "direction": "left", "speed": 5}',
                    '{"cmd": "move_left", "speed": 3, "channel": 0}',
                    '{"ptz": {"move": "left", "velocity": 50}}'
                ]
            },
            # 可能的二进制格式
            {
                "type": "Binary_Hex",
                "examples": [
                    "080112061a020801",  # 可能的protobuf
                    "0a0408011206",      # 另一种protobuf格式
                    "12345678"           # 简单的命令码
                ]
            }
        ]

        payload_file = f"grpc_test_payloads_{self.timestamp}.txt"

        with open(payload_file, 'w', encoding='utf-8') as f:
            f.write("# gRPC PTZ测试Payload集合\n\n")

            for payload_group in test_payloads:
                f.write(f"## {payload_group['type']} 格式:\n")
                for example in payload_group['examples']:
                    f.write(f"   {example}\n")
                f.write("\n")

        self.log(f"🧪 测试Payload已生成: {payload_file}")

    def create_curl_template(self):
        """创建curl测试模板"""

        curl_template = f"""#!/bin/bash
# gRPC PTZ控制测试命令
# 基于发现的 /ipc/grpc_cmd 端点

CAMERA_IP="192.168.31.146"
USERNAME="admin"
PASSWORD="admin123"
GRPC_URL="https://$CAMERA_IP/ipc/grpc_cmd"

echo "🔧 gRPC PTZ控制测试"
echo "===================="

# 测试1: JSON Payload
echo "测试 1: JSON格式PTZ命令"
curl -k -u $USERNAME:$PASSWORD \\
    -X POST \\
    -H "Content-Type: application/json" \\
    -H "Accept: application/json" \\
    -d '{{"command": "ptz", "action": "move", "direction": "left", "speed": 5}}' \\
    "$GRPC_URL"

echo ""

# 测试2: protobuf格式 (需要从浏览器获取真实payload)
echo "测试 2: ProtoBuf格式PTZ命令"
echo "# 需要从浏览器开发者工具获取真实的Payload"
echo "# curl -k -u $USERNAME:$PASSWORD -X POST -H 'Content-Type: application/grpc-web+proto' --data-binary @payload.bin $GRPC_URL"

echo ""

# 测试3: 模拟浏览器请求
echo "测试 3: 模拟浏览器请求"
curl -k -u $USERNAME:$PASSWORD \\
    -X POST \\
    -H "Content-Type: application/grpc-web+proto" \\
    -H "Accept: application/grpc-web+proto" \\
    -H "User-Agent: Mozilla/5.0" \\
    -H "Origin: https://$CAMERA_IP" \\
    -H "Referer: https://$CAMERA_IP/setting.html" \\
    --data-raw "[从浏览器粘贴真实payload]" \\
    "$GRPC_URL"
"""

        curl_file = f"grpc_ptz_test_{self.timestamp}.sh"
        with open(curl_file, 'w') as f:
            f.write(curl_template)

        self.log(f"📋 curl测试模板已生成: {curl_file}")

        return curl_file

    def run_analysis(self):
        """运行分析"""

        self.log("🚀 开始gRPC PTZ协议分析...")

        # 1. 创建详细提取指南
        self.create_extraction_guide()

        # 2. 分析gRPC模式
        self.analyze_grpc_patterns()

        # 3. 生成测试Payload
        self.generate_test_payloads()

        # 4. 创建curl模板
        self.create_curl_template()

        self.log("✅ gRPC分析完成，请按指南获取详细请求信息")

def main():
    print("🔍 gRPC PTZ控制协议分析工具")
    print("=" * 50)

    analyzer = GrpcPTZAnalyzer()

    try:
        analyzer.run_analysis()
        print(f"\n📝 详细日志: {analyzer.log_file}")

    except Exception as e:
        print(f"❌ 分析出错: {e}")

if __name__ == "__main__":
    main()