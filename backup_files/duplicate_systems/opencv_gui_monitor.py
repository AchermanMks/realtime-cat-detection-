#!/usr/bin/env python3
"""
基于OpenCV GUI的实时摄像头监控系统
集成AI分析、数据统计、报警功能
"""

import cv2
import torch
import time
import threading
import queue
import json
import numpy as np
import sqlite3
from datetime import datetime
from collections import deque
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from robot_vision_config import Config
from PIL import Image, ImageDraw, ImageFont
import platform

class OpenCVMonitorGUI:
    """基于OpenCV的监控GUI系统"""

    def __init__(self):
        # 摄像头配置
        self.camera_url = Config.RTSP_URL
        self.backup_camera = 0

        # VLM模型
        self.model = None
        self.processor = None
        self.model_loaded = False

        # 视频流
        self.cap = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()

        # 分析相关
        self.analysis_queue = queue.Queue(maxsize=5)
        self.analysis_history = deque(maxlen=50)
        self.latest_analysis = None
        self.analysis_interval = Config.ANALYSIS_INTERVAL
        self.last_analysis_time = 0

        # 统计数据
        self.stats = {
            'start_time': time.time(),
            'total_frames': 0,
            'total_analyses': 0,
            'fps': 0,
            'alerts_triggered': 0
        }

        # GUI配置
        self.window_name = "🎥 AI智能监控系统"
        self.display_scale = 0.8
        self.info_panel_height = 200

        # 控制面板状态
        self.control_panel = {
            'show_info': True,
            'show_analysis': True,
            'auto_save': False,
            'recording': False,
            'alert_enabled': True
        }

        # 数据库
        self.db_path = "monitoring_data.db"
        self.init_database()

        # 报警配置
        self.alert_cooldown = 30
        self.last_alert_time = 0

        # 中文字体设置
        self.font = self.load_chinese_font()

        print("🚀 OpenCV监控GUI系统初始化完成")

    def load_chinese_font(self, font_size=16):
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
                    "/usr/share/fonts/truetype/arphic/ukai.ttc"
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

    def draw_text_chinese(self, img, text, position, font_size=16, color=(255, 255, 255)):
        """在图像上绘制中文文字"""
        try:
            # 将OpenCV图像转换为PIL图像
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)

            # 如果需要不同字体大小，重新加载字体
            if hasattr(self, 'font') and self.font:
                if font_size != 16:  # 默认字体大小是16
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

    def init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    analysis_text TEXT,
                    objects TEXT,
                    persons TEXT,
                    vehicles TEXT,
                    risk_level TEXT,
                    analysis_time REAL,
                    frame_data BLOB
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    alert_type TEXT,
                    description TEXT,
                    frame_data BLOB
                )
            ''')

            conn.commit()
            conn.close()
            print("✅ 数据库初始化完成")

        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")

    def load_vlm_model(self):
        """加载VLM模型"""
        try:
            print("🤖 正在加载AI视觉模型...")
            start_time = time.time()

            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                Config.MODEL_ID,
                torch_dtype=Config.TORCH_DTYPE,
                device_map=Config.DEVICE_MAP,
            )
            self.processor = AutoProcessor.from_pretrained(Config.MODEL_ID)

            load_time = time.time() - start_time
            self.model_loaded = True

            device = "CUDA" if torch.cuda.is_available() else "CPU"
            print(f"✅ AI模型加载完成 - 设备: {device}, 耗时: {load_time:.2f}秒")
            return True

        except Exception as e:
            print(f"❌ AI模型加载失败: {e}")
            return False

    def connect_camera(self):
        """连接摄像头"""
        try:
            print(f"📡 连接摄像头: {self.camera_url}")
            self.cap = cv2.VideoCapture(self.camera_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 设置分辨率
            if Config.FRAME_WIDTH and Config.FRAME_HEIGHT:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.FRAME_HEIGHT)

            # 测试连接
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                print(f"✅ 主摄像头连接成功: {w}x{h} @{fps:.1f}fps")
                return True
            else:
                print("⚠️ 主摄像头连接失败，尝试本地摄像头")
                self.cap.release()
                self.cap = cv2.VideoCapture(self.backup_camera)
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    print("✅ 本地摄像头连接成功")
                    return True
                else:
                    return False

        except Exception as e:
            print(f"❌ 摄像头连接失败: {e}")
            return False

    def capture_frames(self):
        """视频帧捕获线程"""
        fps_counter = 0
        last_fps_time = time.time()

        while self.running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()

                if ret and frame is not None:
                    # 更新统计
                    self.stats['total_frames'] += 1
                    fps_counter += 1
                    current_time = time.time()

                    # 计算FPS
                    if current_time - last_fps_time >= 1.0:
                        self.stats['fps'] = fps_counter / (current_time - last_fps_time)
                        fps_counter = 0
                        last_fps_time = current_time

                    # 存储当前帧
                    with self.frame_lock:
                        self.current_frame = frame.copy()

                    # 提交AI分析
                    if current_time - self.last_analysis_time > self.analysis_interval:
                        if not self.analysis_queue.full():
                            self.analysis_queue.put((frame.copy(), current_time))
                            self.last_analysis_time = current_time
                else:
                    print("⚠️ 读取帧失败，尝试重连...")
                    time.sleep(1)
                    self.reconnect_camera()

            except Exception as e:
                print(f"帧捕获异常: {e}")
                time.sleep(1)

    def reconnect_camera(self):
        """重新连接摄像头"""
        try:
            if self.cap:
                self.cap.release()
            time.sleep(2)
            self.connect_camera()
        except Exception as e:
            print(f"重连失败: {e}")

    def analysis_worker(self):
        """AI分析工作线程"""
        while self.running:
            try:
                frame, timestamp = self.analysis_queue.get(timeout=1)

                print("🔍 开始AI分析...")
                start_time = time.time()

                result = self.analyze_frame(frame)
                analysis_time = time.time() - start_time

                if result:
                    result['timestamp'] = timestamp
                    result['analysis_time'] = analysis_time

                    # 更新分析结果
                    self.latest_analysis = result
                    self.analysis_history.append(result)
                    self.stats['total_analyses'] += 1

                    # 保存到数据库
                    self.save_analysis_to_db(result, frame)

                    # 检查报警
                    self.check_alerts(result, frame)

                    print(f"✅ AI分析完成 ({analysis_time:.2f}秒)")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"分析异常: {e}")

    def analyze_frame(self, frame):
        """分析单帧"""
        try:
            # 保存临时图片
            temp_path = "/tmp/monitor_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建分析消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": """分析监控画面，请用JSON格式回复：
{
    "scene_description": "场景描述",
    "objects": ["检测到的物体"],
    "persons": {"count": 0, "activities": ["活动"]},
    "vehicles": ["车辆类型"],
    "anomalies": ["异常情况"],
    "risk_level": "低/中/高",
    "summary": "简要总结(不超过50字)"
}"""},
                    ],
                }
            ]

            # VLM处理
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda" if torch.cuda.is_available() else "cpu")

            generated_ids = self.model.generate(**inputs, max_new_tokens=200)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            # 解析结果
            return self.parse_analysis_result(output_text)

        except Exception as e:
            print(f"分析失败: {e}")
            return None

    def parse_analysis_result(self, output_text):
        """解析分析结果"""
        try:
            import re
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)

            if json_match:
                try:
                    parsed_data = json.loads(json_match.group())
                    result = {
                        "raw_text": output_text,
                        "scene_description": parsed_data.get("scene_description", ""),
                        "objects": parsed_data.get("objects", []),
                        "persons": parsed_data.get("persons", {}),
                        "vehicles": parsed_data.get("vehicles", []),
                        "anomalies": parsed_data.get("anomalies", []),
                        "risk_level": parsed_data.get("risk_level", "低"),
                        "summary": parsed_data.get("summary", output_text[:50])
                    }
                    return result
                except json.JSONDecodeError:
                    pass

            # 备用解析
            return {
                "raw_text": output_text,
                "scene_description": output_text[:100],
                "objects": [],
                "persons": {},
                "vehicles": [],
                "anomalies": [],
                "risk_level": "低",
                "summary": output_text[:50] if output_text else "分析中..."
            }

        except Exception as e:
            print(f"解析失败: {e}")
            return {"error": str(e), "summary": "解析错误"}

    def create_info_overlay(self, frame):
        """创建信息叠加层"""
        h, w = frame.shape[:2]

        if not self.control_panel['show_info']:
            return frame

        # 创建信息面板
        info_height = self.info_panel_height
        overlay = np.zeros((info_height, w, 3), dtype=np.uint8)
        overlay[:] = (40, 40, 40)  # 深灰色背景

        # 系统信息
        line_height = 30
        y_pos = 25
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 第一行 - 时间和状态
        text = f"📹 AI智能监控系统  📅 {current_time}"
        overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                       font_size=16, color=(0, 255, 255))

        y_pos += line_height
        # 第二行 - FPS和统计
        uptime = time.time() - self.stats['start_time']
        uptime_str = f"{int(uptime//3600):02d}:{int((uptime%3600)//60):02d}:{int(uptime%60):02d}"
        text = f"📊 帧率: {self.stats['fps']:.1f} FPS  ⏰ 运行时间: {uptime_str}  🔍 分析次数: {self.stats['total_analyses']}"
        overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                       font_size=14, color=(0, 255, 0))

        # AI分析结果
        if self.control_panel['show_analysis'] and self.latest_analysis:
            y_pos += line_height + 5

            analysis = self.latest_analysis
            age = time.time() - analysis.get('timestamp', 0)

            # 风险级别颜色
            risk_level = analysis.get('risk_level', '低')
            risk_color = (0, 255, 0) if risk_level == '低' else (0, 255, 255) if risk_level == '中' else (0, 0, 255)

            text = f"🤖 AI分析结果 ({age:.0f}秒前):"
            overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                           font_size=14, color=(255, 255, 255))

            y_pos += line_height

            # 场景描述
            summary = analysis.get('summary', '')
            if len(summary) > 50:
                summary = summary[:47] + "..."
            text = f"📝 场景描述: {summary}"
            overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                           font_size=13, color=(200, 200, 200))

            y_pos += line_height

            # 风险级别和异常
            text = f"🚨 风险级别: {risk_level}"
            overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                           font_size=14, color=risk_color)

            anomalies = analysis.get('anomalies', [])
            if anomalies:
                y_pos += line_height
                anomaly_text = ', '.join(anomalies[:2])  # 只显示前两个异常
                if len(anomaly_text) > 40:
                    anomaly_text = anomaly_text[:37] + "..."
                text = f"⚠️ 检测异常: {anomaly_text}"
                overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                               font_size=13, color=(0, 165, 255))

        # 控制提示
        y_pos = info_height - 35
        text = "🎮 控制键: Q-退出 S-截图 空格-暂停 I-信息切换 A-分析切换 R-录制"
        overlay = self.draw_text_chinese(overlay, text, (15, y_pos),
                                       font_size=12, color=(150, 150, 150))

        # 合并到主帧
        result = frame.copy()
        result = np.vstack((overlay, result))

        return result

    def check_alerts(self, result, frame):
        """检查报警条件"""
        if not self.control_panel['alert_enabled']:
            return

        current_time = time.time()
        if current_time - self.last_alert_time < self.alert_cooldown:
            return

        alert_triggered = False
        alert_messages = []

        # 检查风险级别
        risk_level = result.get('risk_level', '低')
        if risk_level in ['高', '中']:
            alert_triggered = True
            alert_messages.append(f"检测到{risk_level}风险")

        # 检查异常
        anomalies = result.get('anomalies', [])
        if anomalies:
            alert_triggered = True
            alert_messages.append(f"异常: {', '.join(anomalies[:2])}")

        if alert_triggered:
            self.last_alert_time = current_time
            self.stats['alerts_triggered'] += 1

            print(f"🚨 触发报警: {'; '.join(alert_messages)}")

            # 保存报警到数据库
            self.save_alert_to_db(alert_messages, frame)

    def save_analysis_to_db(self, result, frame):
        """保存分析结果到数据库"""
        try:
            # 压缩帧数据
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_data = buffer.tobytes()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO analysis_history (
                    timestamp, analysis_text, objects, persons, vehicles,
                    risk_level, analysis_time, frame_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.get('timestamp', time.time()),
                result.get('raw_text', ''),
                json.dumps(result.get('objects', [])),
                json.dumps(result.get('persons', {})),
                json.dumps(result.get('vehicles', [])),
                result.get('risk_level', '低'),
                result.get('analysis_time', 0),
                frame_data
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"保存分析结果失败: {e}")

    def save_alert_to_db(self, alert_messages, frame):
        """保存报警到数据库"""
        try:
            # 压缩帧数据
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = buffer.tobytes()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, description, frame_data)
                VALUES (?, ?, ?, ?)
            ''', (
                time.time(),
                "风险检测",
                '; '.join(alert_messages),
                frame_data
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"保存报警失败: {e}")

    def handle_key_input(self, key):
        """处理按键输入"""
        if key == ord('q') or key == 27:  # Q键或ESC退出
            return False
        elif key == ord('s'):  # S键截图
            self.take_screenshot()
        elif key == ord(' '):  # 空格键暂停
            print("⏸️ 按任意键继续...")
            cv2.waitKey(0)
            print("▶️ 继续监控")
        elif key == ord('i'):  # I键切换信息显示
            self.control_panel['show_info'] = not self.control_panel['show_info']
            status = "开启" if self.control_panel['show_info'] else "关闭"
            print(f"ℹ️ 信息显示: {status}")
        elif key == ord('a'):  # A键切换分析显示
            self.control_panel['show_analysis'] = not self.control_panel['show_analysis']
            status = "开启" if self.control_panel['show_analysis'] else "关闭"
            print(f"🤖 分析显示: {status}")
        elif key == ord('r'):  # R键录制（待实现）
            print("📹 录制功能待实现")
        elif key == ord('h'):  # H键帮助
            self.show_help()

        return True

    def take_screenshot(self):
        """截图功能"""
        try:
            with self.frame_lock:
                if self.current_frame is not None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.jpg"
                    cv2.imwrite(filename, self.current_frame)
                    print(f"📸 截图已保存: {filename}")
        except Exception as e:
            print(f"📸 截图失败: {e}")

    def show_help(self):
        """显示帮助信息"""
        help_text = """
🎯 控制说明:
Q/ESC - 退出程序
S     - 截图保存
SPACE - 暂停/继续
I     - 切换信息显示
A     - 切换AI分析显示
R     - 录制功能(待实现)
H     - 显示此帮助
        """
        print(help_text)

    def display_loop(self):
        """主显示循环"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1200, 800)

        print("🖥️ 开始实时显示...")
        print("💡 按 H 键查看控制说明")

        while self.running:
            try:
                with self.frame_lock:
                    if self.current_frame is not None:
                        # 创建显示帧
                        display_frame = self.create_info_overlay(self.current_frame.copy())

                        # 缩放显示
                        if self.display_scale != 1.0:
                            h, w = display_frame.shape[:2]
                            new_w = int(w * self.display_scale)
                            new_h = int(h * self.display_scale)
                            display_frame = cv2.resize(display_frame, (new_w, new_h))

                        # 显示
                        cv2.imshow(self.window_name, display_frame)

                # 处理按键
                key = cv2.waitKey(1) & 0xFF
                if key != 255:  # 有按键输入
                    if not self.handle_key_input(key):
                        break

                time.sleep(0.01)

            except Exception as e:
                print(f"显示异常: {e}")
                time.sleep(0.1)

        cv2.destroyAllWindows()

    def start_system(self):
        """启动监控系统"""
        print("🚀 启动AI智能监控系统...")

        # 加载AI模型
        if not self.load_vlm_model():
            print("❌ 无法加载AI模型，系统退出")
            return False

        # 连接摄像头
        if not self.connect_camera():
            print("❌ 无法连接摄像头，系统退出")
            return False

        self.running = True
        self.stats['start_time'] = time.time()

        # 启动工作线程
        self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)

        self.capture_thread.start()
        self.analysis_thread.start()

        print("✅ 系统启动成功")

        # 主显示循环
        try:
            self.display_loop()
        except KeyboardInterrupt:
            print("\n🛑 接收到中断信号")
        finally:
            self.stop_system()

        return True

    def stop_system(self):
        """停止系统"""
        print("🛑 正在停止监控系统...")
        self.running = False

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()

        # 输出统计信息
        total_time = time.time() - self.stats['start_time']
        print("\n📊 运行统计:")
        print(f"   运行时间: {total_time:.1f}秒")
        print(f"   总帧数: {self.stats['total_frames']:,}")
        print(f"   AI分析: {self.stats['total_analyses']}次")
        print(f"   报警次数: {self.stats['alerts_triggered']}")
        print(f"   平均FPS: {self.stats['total_frames']/total_time:.1f}")

        print("✅ 系统已完全停止")

def main():
    """主函数"""
    print("🎥 AI智能监控系统 - OpenCV GUI版本")
    print("=" * 50)

    try:
        monitor = OpenCVMonitorGUI()
        monitor.start_system()
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")

if __name__ == "__main__":
    main()