#!/usr/bin/env python3
"""
简化版摄像头VLM测试
专注核心功能：摄像头获取 + VLM分析
"""

import cv2
import torch
import time
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import threading
import signal
import sys
import os

class SimpleCameraVLM:
    def __init__(self):
        self.camera_url = "rtsp://192.168.31.146:8554/unicast"
        self.model = None
        self.processor = None
        self.running = False
        self.frame_count = 0

    def load_vlm_model(self):
        """加载VLM模型"""
        print("🤖 加载VLM模型...")
        start_time = time.time()

        try:
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype="auto",
                device_map="auto",
            )
            self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

            load_time = time.time() - start_time
            print(f"✅ VLM模型加载完成，耗时: {load_time:.2f}秒")
            return True

        except Exception as e:
            print(f"❌ VLM模型加载失败: {e}")
            return False

    def get_camera_frame(self):
        """获取摄像头帧"""
        try:
            cap = cv2.VideoCapture(self.camera_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()

                if ret and frame is not None:
                    return frame
                else:
                    print("❌ 无法读取摄像头帧")
                    return None
            else:
                print("❌ 无法连接摄像头")
                return None

        except Exception as e:
            print(f"❌ 摄像头错误: {e}")
            return None

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            # 保存临时图片
            temp_path = "/tmp/current_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": "请分析这个图像并描述看到的内容，包括主要物体、场景和活动。"},
                    ],
                }
            ]

            # 处理输入
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda" if torch.cuda.is_available() else "cpu")

            # 生成回复
            print("🔍 VLM分析中...")
            start_time = time.time()

            generated_ids = self.model.generate(**inputs, max_new_tokens=200)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            analysis_time = time.time() - start_time
            print(f"✅ 分析完成，耗时: {analysis_time:.2f}秒")

            return output_text

        except Exception as e:
            print(f"❌ VLM分析失败: {e}")
            return None

    def run_continuous(self):
        """连续模式运行"""
        print("🎬 开始连续监控模式...")
        print("按 Ctrl+C 停止")

        self.running = True

        try:
            while self.running:
                # 获取摄像头帧
                frame = self.get_camera_frame()

                if frame is not None:
                    self.frame_count += 1
                    h, w = frame.shape[:2]

                    print(f"\n📷 帧 {self.frame_count}: {w}x{h}")

                    # VLM分析
                    result = self.analyze_frame(frame)

                    if result:
                        print("🎯 分析结果:")
                        print(f"   {result}")

                        # 保存分析帧
                        save_path = f"analyzed_frame_{self.frame_count}.jpg"
                        cv2.imwrite(save_path, frame)
                        print(f"💾 已保存: {save_path}")

                    else:
                        print("❌ 分析失败")

                else:
                    print("❌ 无法获取摄像头帧")

                # 等待间隔
                print("⏳ 等待5秒...")
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n🛑 用户中断")

        finally:
            self.running = False
            print("✅ 程序结束")

    def test_single_frame(self):
        """单帧测试模式"""
        print("📷 单帧测试模式")

        # 获取一帧
        frame = self.get_camera_frame()

        if frame is None:
            print("❌ 无法获取摄像头帧")
            return False

        h, w = frame.shape[:2]
        print(f"✅ 获取帧成功: {w}x{h}")

        # 保存测试帧
        cv2.imwrite("test_frame.jpg", frame)
        print("💾 测试帧已保存: test_frame.jpg")

        # VLM分析
        result = self.analyze_frame(frame)

        if result:
            print("🎯 VLM分析结果:")
            print("-" * 40)
            print(result)
            print("-" * 40)
            return True
        else:
            print("❌ VLM分析失败")
            return False

def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n🛑 接收到停止信号")
    sys.exit(0)

def main():
    """主函数"""
    print("🎥 简化版摄像头VLM测试")
    print("=" * 50)

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建实例
    vlm_system = SimpleCameraVLM()

    # 加载模型
    if not vlm_system.load_vlm_model():
        print("❌ 系统初始化失败")
        return

    # 选择模式
    print("\n请选择测试模式:")
    print("1. 单帧测试")
    print("2. 连续监控")

    try:
        choice = input("输入选择 (1/2): ").strip()

        if choice == "1":
            vlm_system.test_single_frame()
        elif choice == "2":
            vlm_system.run_continuous()
        else:
            print("❌ 无效选择，默认执行单帧测试")
            vlm_system.test_single_frame()

    except (EOFError, KeyboardInterrupt):
        print("\n🔄 自动执行单帧测试...")
        vlm_system.test_single_frame()

if __name__ == "__main__":
    main()