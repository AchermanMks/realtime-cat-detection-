#!/usr/bin/env python3
"""
虚拟摄像头 + VLM实时分析演示
在没有物理摄像头的情况下演示VLM视觉分析功能
"""

import cv2
import torch
import time
import threading
import queue
import numpy as np
import signal
import sys
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

class VirtualCameraVLM:
    def __init__(self):
        self.model = None
        self.processor = None
        self.running = False

        # 虚拟摄像头相关
        self.frame_queue = queue.Queue(maxsize=30)
        self.current_frame = None
        self.frame_count = 0

        # VLM分析相关
        self.analysis_queue = queue.Queue(maxsize=3)
        self.latest_analysis = None
        self.analysis_counter = 0
        self.last_analysis_time = 0
        self.analysis_interval = 5.0  # 每5秒分析一次

        # 显示设置
        self.window_name = "🎥 虚拟摄像头 + AI视觉分析演示"

    def load_vlm_model(self):
        """加载VLM模型"""
        print("🤖 正在加载VLM模型...")
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

    def generate_virtual_frames(self):
        """生成虚拟摄像头帧"""
        print("📹 启动虚拟摄像头...")

        # 场景类型
        scenes = [
            {"name": "移动圆圈", "color": (0, 255, 255), "shape": "circle"},
            {"name": "旋转矩形", "color": (255, 0, 255), "shape": "rectangle"},
            {"name": "随机点阵", "color": (0, 255, 0), "shape": "dots"},
            {"name": "波浪线条", "color": (255, 255, 0), "shape": "waves"}
        ]

        current_scene = 0
        scene_duration = 150  # 每个场景150帧（5秒）

        while self.running:
            try:
                # 创建黑色背景
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

                # 当前场景
                scene = scenes[current_scene]
                t = self.frame_count * 0.1

                # 根据场景类型绘制不同内容
                if scene["shape"] == "circle":
                    # 移动圆圈
                    center_x = int(320 + 200 * np.sin(t))
                    center_y = int(240 + 100 * np.cos(t * 0.7))
                    cv2.circle(frame, (center_x, center_y), 40, scene["color"], -1)
                    cv2.circle(frame, (center_x, center_y), 60, (255, 255, 255), 2)

                elif scene["shape"] == "rectangle":
                    # 旋转矩形
                    center = (320, 240)
                    size = (80, 40)
                    angle = t * 20
                    box = cv2.boxPoints(((center), size, angle))
                    box = np.asarray(box, dtype=int)
                    cv2.drawContours(frame, [box], 0, scene["color"], -1)

                elif scene["shape"] == "dots":
                    # 随机点阵
                    for i in range(20):
                        x = int(320 + 250 * np.sin(t + i * 0.5))
                        y = int(240 + 150 * np.cos(t * 0.3 + i * 0.8))
                        cv2.circle(frame, (x, y), 8, scene["color"], -1)

                elif scene["shape"] == "waves":
                    # 波浪线条
                    points = []
                    for x in range(0, 640, 5):
                        y = int(240 + 100 * np.sin((x + t * 50) * 0.01))
                        points.append([x, y])
                    points = np.array(points, dtype=np.int32)
                    cv2.polylines(frame, [points], False, scene["color"], 3)

                # 添加场景信息
                cv2.putText(frame, f"场景: {scene['name']}",
                           (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"帧号: {self.frame_count}",
                           (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                cv2.putText(frame, f"时间: {self.frame_count/30:.1f}s",
                           (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

                # 添加AI分析状态
                if self.latest_analysis:
                    age = time.time() - self.latest_analysis['timestamp']
                    analysis_text = self.latest_analysis['text'][:60] + "..." if len(self.latest_analysis['text']) > 60 else self.latest_analysis['text']
                    cv2.putText(frame, f"AI分析 ({age:.0f}s前): {analysis_text}",
                               (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
                    cv2.putText(frame, f"分析次数: {self.analysis_counter}",
                               (20, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
                else:
                    cv2.putText(frame, "AI分析: 等待中...",
                               (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 100), 2)

                # 更新帧
                self.current_frame = frame.copy()
                self.frame_count += 1

                # 放入显示队列
                if not self.frame_queue.full():
                    self.frame_queue.put(frame.copy())
                else:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame.copy())
                    except queue.Empty:
                        pass

                # 提交VLM分析
                current_time = time.time()
                if current_time - self.last_analysis_time > self.analysis_interval:
                    if not self.analysis_queue.full():
                        self.analysis_queue.put(frame.copy())
                        self.last_analysis_time = current_time

                # 切换场景
                if self.frame_count % scene_duration == 0:
                    current_scene = (current_scene + 1) % len(scenes)
                    print(f"🎬 切换到场景: {scenes[current_scene]['name']}")

                time.sleep(1/30)  # 30fps

            except Exception as e:
                print(f"虚拟摄像头异常: {e}")
                time.sleep(0.1)

    def analysis_worker(self):
        """VLM分析工作线程"""
        while self.running:
            try:
                frame = self.analysis_queue.get(timeout=1)

                print("🔍 开始VLM分析虚拟场景...")
                start_time = time.time()

                result = self.analyze_frame(frame)
                analysis_time = time.time() - start_time

                if result:
                    self.latest_analysis = {
                        'text': result,
                        'timestamp': time.time(),
                        'analysis_time': analysis_time
                    }
                    self.analysis_counter += 1
                    print(f"✅ VLM分析完成 ({analysis_time:.2f}秒)")
                    print(f"🎯 分析结果: {result}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ VLM分析异常: {e}")

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            temp_path = "/tmp/virtual_frame.jpg"
            cv2.imwrite(temp_path, frame)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": "这是一个虚拟摄像头生成的图像。请描述你看到的几何形状、颜色、运动状态和整体场景特点。"},
                    ],
                }
            ]

            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda" if torch.cuda.is_available() else "cpu")

            generated_ids = self.model.generate(**inputs, max_new_tokens=150)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            return output_text.strip()

        except Exception as e:
            print(f"VLM分析失败: {e}")
            return None

    def display_loop(self):
        """显示循环"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)

        print("🖥️  开始实时显示...")
        print("💡 按键说明:")
        print("   'q' - 退出程序")
        print("   's' - 截图保存")
        print("   'space' - 暂停/继续")

        paused = False

        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get_nowait()

                    if not paused:
                        cv2.imshow(self.window_name, frame)

                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    print("🛑 用户退出")
                    break
                elif key == ord('s'):
                    if self.current_frame is not None:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"virtual_screenshot_{timestamp}.jpg"
                        cv2.imwrite(filename, self.current_frame)
                        print(f"📸 截图已保存: {filename}")
                elif key == ord(' '):
                    paused = not paused
                    status = "暂停" if paused else "继续"
                    print(f"⏸️  显示{status}")

            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                print(f"显示异常: {e}")

        cv2.destroyAllWindows()

    def start_system(self):
        """启动系统"""
        print("🚀 启动虚拟摄像头VLM分析系统...")

        # 加载模型
        if not self.load_vlm_model():
            return False

        self.running = True

        # 启动线程
        camera_thread = threading.Thread(target=self.generate_virtual_frames, daemon=True)
        analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)

        camera_thread.start()
        analysis_thread.start()

        # 主显示循环
        try:
            self.display_loop()
        except KeyboardInterrupt:
            print("\n🛑 接收到中断信号")
        finally:
            self.stop_system()

    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止系统...")
        self.running = False
        cv2.destroyAllWindows()
        print("✅ 系统已停止")

def signal_handler(signum, frame):
    """信号处理"""
    print("\n🛑 接收到停止信号")
    sys.exit(0)

def main():
    """主函数"""
    print("🎥 虚拟摄像头 + VLM分析演示系统")
    print("=" * 50)
    print("📝 说明: 本演示使用虚拟生成的动态图像来展示VLM实时分析能力")
    print("🎯 功能: 自动切换场景，AI每5秒分析一次虚拟场景内容")
    print("=" * 50)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    system = VirtualCameraVLM()
    system.start_system()

if __name__ == "__main__":
    main()