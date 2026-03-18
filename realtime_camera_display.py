#!/usr/bin/env python3
"""
实时摄像头显示 + VLM分析系统
显示摄像头实时画面，叠加AI分析结果
"""

import cv2
import torch
import time
import threading
import queue
import numpy as np
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import signal
import sys
from PIL import Image, ImageDraw, ImageFont
import platform

class RealtimeCameraVLM:
    def __init__(self):
        self.camera_url = "rtsp://192.168.31.146:8554/unicast"
        self.model = None
        self.processor = None
        self.running = False

        # 视频流相关
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=30)
        self.current_frame = None
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.display_fps = 0

        # VLM分析相关
        self.analysis_queue = queue.Queue(maxsize=5)
        self.latest_analysis = None
        self.analysis_counter = 0
        self.last_analysis_time = 0

        # 显示设置
        self.window_name = "🎥 实时摄像头 + AI视觉分析"
        self.display_scale = 0.6  # 显示缩放比例
        self.analysis_interval = 8.0  # VLM分析间隔(秒)

        # 中文字体设置
        self.font = self.load_chinese_font()

    def load_chinese_font(self, font_size=20):
        """加载中文字体"""
        try:
            # 根据系统选择合适的中文字体
            system = platform.system()
            if system == "Windows":
                font_paths = [
                    "C:/Windows/Fonts/simhei.ttf",  # 黑体
                    "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
                    "C:/Windows/Fonts/simsun.ttc"   # 宋体
                ]
            elif system == "Darwin":  # macOS
                font_paths = [
                    "/System/Library/Fonts/PingFang.ttc",
                    "/System/Library/Fonts/Helvetica.ttc"
                ]
            else:  # Linux
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                    "/usr/share/fonts/truetype/arphic/ukai.ttc",
                    "/System/Library/Fonts/Arial.ttf"
                ]

            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    print(f"✅ 加载中文字体: {font_path}")
                    return font
                except (OSError, IOError):
                    continue

            print("⚠️ 未找到中文字体，使用默认字体")
            return ImageFont.load_default()

        except Exception as e:
            print(f"⚠️ 字体加载异常: {e}")
            return ImageFont.load_default()

    def draw_text_chinese(self, img, text, position, font_size=20, color=(255, 255, 255)):
        """在图像上绘制中文文字"""
        try:
            # 将OpenCV图像转换为PIL图像
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)

            # 如果需要不同字体大小，重新加载字体
            if hasattr(self, 'font') and self.font:
                if font_size != 20:  # 默认字体大小是20
                    font = self.load_chinese_font(font_size)
                else:
                    font = self.font
            else:
                font = self.load_chinese_font(font_size)

            # 绘制文字（先绘制黑色描边）
            x, y = position
            draw.text((x+1, y+1), text, font=font, fill=(0, 0, 0))  # 黑色描边
            draw.text((x, y), text, font=font, fill=color)  # 主要文字

            # 转换回OpenCV格式
            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            return img_cv

        except Exception as e:
            print(f"绘制中文文字失败: {e}")
            # 如果失败，回退到OpenCV的putText（可能显示乱码）
            cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
            return img

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

    def connect_camera(self):
        """连接摄像头"""
        try:
            print(f"📡 连接摄像头: {self.camera_url}")
            self.cap = cv2.VideoCapture(self.camera_url)

            # 设置缓冲区大小
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 测试连接
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"✅ 摄像头连接成功")
                print(f"   分辨率: {w}x{h}")
                print(f"   帧率: {fps}")
                return True
            else:
                print("❌ 无法获取测试帧")
                return False

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def capture_frames(self):
        """视频帧捕获线程"""
        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    # 更新FPS计数
                    self.fps_counter += 1
                    current_time = time.time()

                    if current_time - self.last_fps_time >= 1.0:
                        self.display_fps = self.fps_counter / (current_time - self.last_fps_time)
                        self.fps_counter = 0
                        self.last_fps_time = current_time

                    # 存储最新帧
                    self.current_frame = frame.copy()

                    # 将帧放入队列供显示
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame.copy())
                    else:
                        # 队列满时丢弃最旧的帧
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put(frame.copy())
                        except queue.Empty:
                            pass

                    # 提交VLM分析
                    if current_time - self.last_analysis_time > self.analysis_interval:
                        if not self.analysis_queue.full():
                            self.analysis_queue.put(frame.copy())
                            self.last_analysis_time = current_time

                else:
                    print("⚠️ 读取帧失败")
                    time.sleep(0.1)

            except Exception as e:
                print(f"⚠️ 帧捕获异常: {e}")
                time.sleep(0.1)

    def analysis_worker(self):
        """VLM分析工作线程"""
        while self.running:
            try:
                # 获取待分析的帧
                frame = self.analysis_queue.get(timeout=1)

                print("🔍 开始VLM分析...")
                start_time = time.time()

                # 执行分析
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
                    print(f"📋 分析结果: {result[:100]}...")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ VLM分析异常: {e}")

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            # 保存临时图片
            temp_path = "/tmp/realtime_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": "简要描述图像中的主要内容，包括：1.场景环境 2.重要物体 3.人物活动。回复要简洁，不超过50字。"},
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
            generated_ids = self.model.generate(**inputs, max_new_tokens=100)
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

    def draw_info_overlay(self, frame):
        """在帧上绘制信息叠加层"""
        overlay_frame = frame.copy()
        h, w = overlay_frame.shape[:2]

        # 创建半透明背景
        overlay = np.zeros((140, w, 3), dtype=np.uint8)
        overlay[:] = (0, 0, 0)

        # 系统信息
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        info_lines = [
            f"📹 实时摄像头监控  📅 {current_time}",
            f"📊 帧率: {self.display_fps:.1f} FPS  🔍 AI分析: {self.analysis_counter}次",
        ]

        # VLM分析结果
        if self.latest_analysis:
            age = time.time() - self.latest_analysis['timestamp']
            analysis_text = self.latest_analysis['text']

            # 截断长文本
            if len(analysis_text) > 60:
                analysis_text = analysis_text[:57] + "..."

            info_lines.append(f"🤖 AI分析结果 ({age:.0f}秒前): {analysis_text}")
        else:
            info_lines.append("🤖 AI分析: 等待分析中...")

        # 绘制文字信息
        for i, line in enumerate(info_lines):
            y_pos = 30 + i * 35
            # 根据行内容选择颜色
            if i == 0:
                color = (0, 255, 255)  # 黄色 - 标题
            elif i == 1:
                color = (255, 255, 255)  # 白色 - 状态信息
            else:
                color = (100, 255, 100)  # 绿色 - AI分析结果

            # 使用中文字体绘制
            overlay = self.draw_text_chinese(overlay, line, (10, y_pos), font_size=16, color=color)

        # 混合叠加层到主画面
        result = overlay_frame.copy()
        result[0:140] = cv2.addWeighted(result[0:140], 0.7, overlay, 0.3, 0)

        return result

    def display_loop(self):
        """显示循环"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)

        print("🖥️  开始实时显示...")
        print("💡 按键说明:")
        print("   'q' - 退出程序")
        print("   's' - 截图保存")
        print("   'f' - 全屏切换")
        print("   'space' - 暂停/继续")

        paused = False

        while self.running:
            try:
                # 获取最新帧
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get_nowait()

                    if not paused:
                        # 添加信息叠加
                        display_frame = self.draw_info_overlay(frame)

                        # 缩放显示
                        if self.display_scale != 1.0:
                            h, w = display_frame.shape[:2]
                            new_w = int(w * self.display_scale)
                            new_h = int(h * self.display_scale)
                            display_frame = cv2.resize(display_frame, (new_w, new_h))

                        # 显示帧
                        cv2.imshow(self.window_name, display_frame)

                # 处理按键
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    print("🛑 用户退出")
                    break
                elif key == ord('s'):
                    if self.current_frame is not None:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshot_{timestamp}.jpg"
                        cv2.imwrite(filename, self.current_frame)
                        print(f"📸 截图已保存: {filename}")
                elif key == ord('f'):
                    # 全屏切换
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
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
        print("🚀 启动实时摄像头显示系统...")

        # 加载模型
        if not self.load_vlm_model():
            return False

        # 连接摄像头
        if not self.connect_camera():
            return False

        self.running = True

        # 启动线程
        capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)

        capture_thread.start()
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

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()
        print("✅ 系统已停止")

def signal_handler(signum, frame):
    """信号处理"""
    print("\n🛑 接收到停止信号")
    sys.exit(0)

def main():
    """主函数"""
    print("🎥 实时摄像头显示 + VLM分析系统")
    print("=" * 50)

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建并启动系统
    system = RealtimeCameraVLM()
    system.start_system()

if __name__ == "__main__":
    main()