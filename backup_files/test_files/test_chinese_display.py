#!/usr/bin/env python3
"""
测试中文显示修复
验证摄像头画面上的中文文字是否正确显示
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import platform
import time

class ChineseDisplayTest:
    """中文显示测试类"""

    def __init__(self):
        self.font = self.load_chinese_font()
        print("🧪 中文显示测试初始化完成")

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
                    "/usr/share/fonts/truetype/arphic/ukai.ttc"
                ]

            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    print(f"✅ 成功加载字体: {font_path}")
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
            if font_size != 20:  # 默认字体大小是20
                font = self.load_chinese_font(font_size)
            else:
                font = self.font

            # 绘制文字（先绘制黑色描边）
            x, y = position
            draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0))  # 黑色描边
            draw.text((x, y), text, font=font, fill=color)  # 主要文字

            # 转换回OpenCV格式
            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            return img_cv

        except Exception as e:
            print(f"绘制中文文字失败: {e}")
            # 如果失败，回退到OpenCV的putText（可能显示乱码）
            cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            return img

    def create_test_frame(self):
        """创建测试图像"""
        # 创建一个黑色背景图像
        height, width = 600, 800
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 测试文字列表
        test_texts = [
            "📹 实时监控系统测试",
            "🤖 人工智能视觉分析",
            "🔍 检测到目标：人员活动",
            "⚠️ 异常行为预警",
            "📊 系统运行正常",
            "🎯 自动跟踪已启用",
            "🚨 安全监控中...",
            "✅ 中文显示修复成功！"
        ]

        # 在图像上绘制测试文字
        for i, text in enumerate(test_texts):
            y_pos = 70 + i * 60
            color_options = [
                (0, 255, 255),   # 黄色
                (0, 255, 0),     # 绿色
                (255, 255, 255), # 白色
                (0, 165, 255),   # 橙色
                (255, 0, 255),   # 紫色
                (0, 255, 255),   # 青色
                (0, 0, 255),     # 红色
                (0, 255, 0)      # 绿色
            ]

            color = color_options[i % len(color_options)]
            frame = self.draw_text_chinese(frame, text, (50, y_pos),
                                         font_size=24, color=color)

        return frame

    def run_test(self):
        """运行测试"""
        print("🚀 开始中文显示测试...")
        print("=" * 50)

        # 创建测试窗口
        window_name = "🧪 中文显示测试 - 按 ESC 退出"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

        print("💡 测试说明:")
        print("   如果看到正确的中文文字，说明修复成功")
        print("   如果看到乱码或方块，说明还需要调整字体")
        print("   按 ESC 键退出测试")
        print()

        try:
            while True:
                # 创建测试帧
                test_frame = self.create_test_frame()

                # 添加动态时间戳
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                timestamp_text = f"⏰ 测试时间: {current_time}"
                test_frame = self.draw_text_chinese(test_frame, timestamp_text,
                                                  (50, 550), font_size=16,
                                                  color=(150, 150, 150))

                # 显示测试帧
                cv2.imshow(window_name, test_frame)

                # 检查按键
                key = cv2.waitKey(100) & 0xFF
                if key == 27:  # ESC键
                    print("🛑 测试结束")
                    break

        except KeyboardInterrupt:
            print("\n🛑 测试被中断")
        finally:
            cv2.destroyAllWindows()
            print("✅ 测试窗口已关闭")

def main():
    """主函数"""
    print("🧪 中文显示修复测试")
    print("=" * 50)

    # 创建测试器并运行
    tester = ChineseDisplayTest()
    tester.run_test()

    print("\n📝 测试总结:")
    print("   如果中文显示正常，监控画面乱码问题已解决")
    print("   可以运行其他监控程序验证效果")
    print("   主要修复文件:")
    print("   - realtime_camera_display.py")
    print("   - robot_vision_main.py")
    print("   - opencv_gui_monitor.py")

if __name__ == "__main__":
    main()