#!/usr/bin/env python3
"""
机器人视觉识别系统主程序
支持RTSP拉流、实时VLM分析、云台控制
"""

import cv2
import time
import threading
import signal
import sys
import numpy as np
from robot_vision_config import Config
from rtsp_streamer import RTSPStreamer
from vision_analyzer import VisionAnalyzer
from ptz_controller import PTZController
from PIL import Image, ImageDraw, ImageFont
import platform

class RobotVisionSystem:
    """机器人视觉识别系统主控制器"""

    def __init__(self):
        self.streamer = RTSPStreamer()
        self.analyzer = VisionAnalyzer()
        self.ptz = PTZController()

        self.running = False
        self.display_window = None
        self.last_control_time = 0
        self.auto_tracking = Config.AUTO_TRACKING

        # 统计信息
        self.stats = {
            "frames_processed": 0,
            "analyses_completed": 0,
            "tracking_actions": 0,
            "start_time": None
        }

        # 中文字体设置
        self.font = self.load_chinese_font()

        print("🤖 机器人视觉识别系统初始化完成")

    def load_chinese_font(self, font_size=18):
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

    def draw_text_chinese(self, img, text, position, font_size=18, color=(255, 255, 255)):
        """在图像上绘制中文文字"""
        try:
            # 将OpenCV图像转换为PIL图像
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)

            # 如果需要不同字体大小，重新加载字体
            if hasattr(self, 'font') and self.font:
                if font_size != 18:  # 默认字体大小是18
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
            cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            return img

    def initialize_system(self):
        """初始化系统所有组件"""
        print("=" * 50)
        print("🚀 正在初始化机器人视觉系统...")
        print("=" * 50)

        # 验证配置
        Config.validate()

        # 1. 测试云台连接
        print("1. 测试云台连接...")
        if not self.ptz.test_connection():
            print("⚠️ 云台连接失败，将以离线模式运行")

        # 2. 加载VLM模型
        print("2. 加载VLM模型...")
        if not self.analyzer.load_model():
            print("❌ VLM模型加载失败，系统无法启动")
            return False

        # 3. 测试RTSP连接
        print("3. 测试RTSP连接...")
        if not self.streamer.test_stream(5):
            print("❌ RTSP流测试失败，请检查配置")
            return False

        print("✅ 系统初始化完成！")
        return True

    def start_system(self):
        """启动系统"""
        if not self.initialize_system():
            return False

        try:
            print("\n🎬 启动视频流获取...")
            if not self.streamer.start_capture():
                print("❌ 视频流启动失败")
                return False

            print("🔍 启动视觉分析...")
            if not self.analyzer.start_analysis():
                print("❌ 视觉分析启动失败")
                return False

            self.running = True
            self.stats["start_time"] = time.time()

            # 创建显示窗口
            if Config.SAVE_FRAMES:
                cv2.namedWindow("Robot Vision", cv2.WINDOW_AUTOSIZE)

            print("\n" + "=" * 50)
            print("🤖 机器人视觉识别系统运行中...")
            print("按 'q' 退出, 按 's' 保存帧, 按 't' 切换自动跟踪")
            print("=" * 50)

            # 主循环
            self._main_loop()

            return True

        except Exception as e:
            print(f"❌ 系统启动异常: {e}")
            return False

    def stop_system(self):
        """停止系统"""
        print("\n🛑 正在停止系统...")
        self.running = False

        # 停止各个组件
        self.streamer.stop_capture()
        self.analyzer.stop_analysis()

        # 关闭显示窗口
        cv2.destroyAllWindows()

        # 输出统计信息
        self._print_final_stats()

        print("✅ 系统已安全关闭")

    def _main_loop(self):
        """主控制循环"""
        while self.running:
            try:
                # 获取最新视频帧
                frame = self.streamer.get_latest_frame()

                if frame is None:
                    time.sleep(0.1)
                    continue

                self.stats["frames_processed"] += 1

                # 提交帧进行分析
                self.analyzer.analyze_frame(frame)

                # 获取最新分析结果
                analysis_result = self.analyzer.get_latest_result()
                if analysis_result:
                    self.stats["analyses_completed"] += 1
                    self._process_analysis_result(analysis_result, frame)

                # 显示视频（如果启用）
                if Config.SAVE_FRAMES:
                    display_frame = self._prepare_display_frame(frame, analysis_result)
                    cv2.imshow("Robot Vision", display_frame)

                    # 处理键盘输入
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('s'):
                        self.streamer.save_frame(frame)
                    elif key == ord('t'):
                        self.auto_tracking = not self.auto_tracking
                        print(f"自动跟踪: {'开启' if self.auto_tracking else '关闭'}")

                # 控制帧率
                time.sleep(0.03)  # ~30fps

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"主循环异常: {e}")
                time.sleep(1)

    def _process_analysis_result(self, result, frame):
        """处理视觉分析结果"""
        try:
            if not result.get("parsed_data"):
                return

            # 打印分析结果
            objects = result.get("objects", [])
            priority_target = result.get("priority_target", "")

            if objects:
                print(f"🎯 检测到对象: {', '.join(objects)}")

            if priority_target:
                print(f"⭐ 优先目标: {priority_target}")

            # 自动跟踪逻辑
            if self.auto_tracking and self._should_track(result):
                self._execute_tracking(result, frame)

        except Exception as e:
            print(f"处理分析结果异常: {e}")

    def _should_track(self, result):
        """判断是否应该进行跟踪"""
        current_time = time.time()

        # 控制跟踪频率
        if current_time - self.last_control_time < 2.0:
            return False

        # 检查是否有优先级目标
        priority_target = result.get("priority_target", "").lower()
        objects = [obj.lower() for obj in result.get("objects", [])]

        # 检查优先级列表
        for priority in Config.TRACK_PRIORITY:
            if priority.lower() in priority_target or any(priority.lower() in obj for obj in objects):
                return True

        return False

    def _execute_tracking(self, result, frame):
        """执行跟踪动作"""
        try:
            h, w = frame.shape[:2]

            # 简化的跟踪逻辑：随机移动云台进行搜索
            tracking_suggestion = result.get("tracking_suggestion", "").lower()

            if "left" in tracking_suggestion or "左" in tracking_suggestion:
                actions = [("pan_left", 30)]
            elif "right" in tracking_suggestion or "右" in tracking_suggestion:
                actions = [("pan_right", 30)]
            elif "up" in tracking_suggestion or "上" in tracking_suggestion:
                actions = [("tilt_up", 20)]
            elif "down" in tracking_suggestion or "下" in tracking_suggestion:
                actions = [("tilt_down", 20)]
            else:
                # 默认搜索模式
                actions = [("auto_scan", 1)]

            # 执行动作
            for action, param in actions:
                if hasattr(self.ptz, action):
                    getattr(self.ptz, action)(param)
                    self.stats["tracking_actions"] += 1
                    print(f"🎮 执行跟踪动作: {action} ({param})")

            self.last_control_time = time.time()

            # 2秒后停止移动
            threading.Timer(2.0, self.ptz.stop).start()

        except Exception as e:
            print(f"执行跟踪异常: {e}")

    def _prepare_display_frame(self, frame, analysis_result):
        """准备显示帧（添加信息覆盖）"""
        display_frame = frame.copy()
        h, w = display_frame.shape[:2]

        # 添加状态信息
        info_text = [
            f"📊 已处理帧数: {self.stats['frames_processed']}",
            f"🔍 完成分析: {self.stats['analyses_completed']}次",
            f"🎯 跟踪动作: {self.stats['tracking_actions']}次",
            f"🤖 自动跟踪: {'开启' if self.auto_tracking else '关闭'}"
        ]

        # 显示系统状态
        for i, text in enumerate(info_text):
            position = (15, 35 + i * 30)
            color = (0, 255, 0)  # 绿色
            display_frame = self.draw_text_chinese(display_frame, text, position,
                                                 font_size=16, color=color)

        # 显示分析结果
        if analysis_result:
            objects = analysis_result.get("objects", [])
            if objects:
                obj_text = f"🎯 检测到对象: {', '.join(objects[:3])}"  # 只显示前3个
                position = (15, h - 40)
                color = (255, 255, 0)  # 黄色
                display_frame = self.draw_text_chinese(display_frame, obj_text, position,
                                                     font_size=16, color=color)

        return display_frame

    def _print_final_stats(self):
        """打印最终统计信息"""
        if self.stats["start_time"]:
            runtime = time.time() - self.stats["start_time"]
            fps = self.stats["frames_processed"] / runtime if runtime > 0 else 0

            print("\n" + "=" * 40)
            print("📊 系统运行统计:")
            print("=" * 40)
            print(f"运行时间: {runtime:.1f} 秒")
            print(f"处理帧数: {self.stats['frames_processed']}")
            print(f"分析次数: {self.stats['analyses_completed']}")
            print(f"跟踪动作: {self.stats['tracking_actions']}")
            print(f"平均FPS: {fps:.1f}")
            print("=" * 40)

    def run_interactive_mode(self):
        """运行交互模式"""
        print("\n🎮 进入交互控制模式")
        print("可用命令:")
        print("  w/s - 上/下移动")
        print("  a/d - 左/右移动")
        print("  +/- - 放大/缩小")
        print("  space - 停止移动")
        print("  p - 设置预设位置")
        print("  g - 移动到预设位置")
        print("  q - 退出")

        while True:
            try:
                cmd = input("\n🎮 输入命令: ").lower().strip()

                if cmd == 'q':
                    break
                elif cmd == 'w':
                    self.ptz.tilt_up()
                elif cmd == 's':
                    self.ptz.tilt_down()
                elif cmd == 'a':
                    self.ptz.pan_left()
                elif cmd == 'd':
                    self.ptz.pan_right()
                elif cmd == '+':
                    self.ptz.zoom_in()
                elif cmd == '-':
                    self.ptz.zoom_out()
                elif cmd == ' ' or cmd == 'space':
                    self.ptz.stop()
                elif cmd == 'p':
                    preset_id = input("输入预设位置ID (1-8): ")
                    try:
                        self.ptz.set_preset(int(preset_id))
                    except ValueError:
                        print("❌ 无效的预设位置ID")
                elif cmd == 'g':
                    preset_id = input("输入要移动到的预设位置ID (1-8): ")
                    try:
                        self.ptz.move_to_preset(int(preset_id))
                    except ValueError:
                        print("❌ 无效的预设位置ID")
                else:
                    print("❌ 未知命令")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"命令执行异常: {e}")

def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n接收到停止信号，正在安全关闭...")
    sys.exit(0)

def main():
    """主函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建系统实例
    system = RobotVisionSystem()

    try:
        # 检查启动参数
        if len(sys.argv) > 1 and sys.argv[1] == "interactive":
            system.run_interactive_mode()
        else:
            system.start_system()

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"系统异常: {e}")
    finally:
        system.stop_system()

if __name__ == "__main__":
    main()