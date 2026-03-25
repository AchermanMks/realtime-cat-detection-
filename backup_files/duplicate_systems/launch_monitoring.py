#!/usr/bin/env python3
"""
监控系统启动器
提供多种监控方式选择
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import importlib.util

class MonitoringLauncher:
    """监控系统启动器"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎥 监控系统启动器")
        self.root.geometry("600x500")
        self.root.configure(bg='#2b2b2b')

        # 监控系统选项
        self.systems = [
            {
                "name": "🖥️ 桌面版实时监控",
                "description": "基于OpenCV的桌面监控界面，支持快捷键操作",
                "script": "realtime_camera_display.py",
                "features": ["实时视频显示", "VLM分析", "快捷键控制", "截图功能"]
            },
            {
                "name": "🌐 Web版监控界面",
                "description": "基于Flask的Web监控，通过浏览器访问",
                "script": "web_camera_stream.py",
                "features": ["Web界面", "远程访问", "实时统计", "移动端兼容"]
            },
            {
                "name": "📊 高级监控仪表板",
                "description": "功能最完整的监控系统，包含数据分析和报警",
                "script": "advanced_monitoring_dashboard.py",
                "features": ["GUI仪表板", "数据库存储", "报警系统", "统计分析", "数据导出"]
            },
            {
                "name": "🧪 简单VLM测试",
                "description": "轻量级摄像头VLM测试工具",
                "script": "simple_camera_vlm.py",
                "features": ["轻量级", "快速测试", "基础分析"]
            }
        ]

        self.setup_gui()

    def setup_gui(self):
        """设置GUI"""
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill=tk.X, padx=20, pady=20)

        title_label = ttk.Label(
            title_frame,
            text="🎥 监控系统启动器",
            font=("Arial", 16, "bold")
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="选择你需要的监控方式",
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(5, 0))

        # 系统选择区域
        systems_frame = ttk.LabelFrame(self.root, text="🚀 可用监控系统", padding="10")
        systems_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 创建系统卡片
        for i, system in enumerate(self.systems):
            self.create_system_card(systems_frame, system, i)

        # 底部按钮
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        check_deps_btn = ttk.Button(
            bottom_frame,
            text="🔍 检查依赖",
            command=self.check_dependencies
        )
        check_deps_btn.pack(side=tk.LEFT, padx=(0, 10))

        install_deps_btn = ttk.Button(
            bottom_frame,
            text="📦 安装依赖",
            command=self.install_dependencies
        )
        install_deps_btn.pack(side=tk.LEFT, padx=(0, 10))

        exit_btn = ttk.Button(
            bottom_frame,
            text="❌ 退出",
            command=self.root.quit
        )
        exit_btn.pack(side=tk.RIGHT)

    def create_system_card(self, parent, system, index):
        """创建系统选择卡片"""
        # 主卡片框架
        card_frame = ttk.LabelFrame(parent, text="", padding="10")
        card_frame.pack(fill=tk.X, pady=5)

        # 左侧信息
        info_frame = ttk.Frame(card_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 系统名称
        name_label = ttk.Label(
            info_frame,
            text=system["name"],
            font=("Arial", 12, "bold")
        )
        name_label.pack(anchor=tk.W)

        # 描述
        desc_label = ttk.Label(
            info_frame,
            text=system["description"],
            wraplength=350
        )
        desc_label.pack(anchor=tk.W, pady=(2, 5))

        # 特性列表
        features_text = "✨ " + " • ".join(system["features"])
        features_label = ttk.Label(
            info_frame,
            text=features_text,
            font=("Arial", 9),
            foreground="blue"
        )
        features_label.pack(anchor=tk.W)

        # 右侧按钮
        btn_frame = ttk.Frame(card_frame)
        btn_frame.pack(side=tk.RIGHT, padx=(10, 0))

        launch_btn = ttk.Button(
            btn_frame,
            text="🚀 启动",
            command=lambda s=system: self.launch_system(s)
        )
        launch_btn.pack()

        # 检查脚本是否存在
        if not os.path.exists(system["script"]):
            launch_btn.config(state=tk.DISABLED)
            missing_label = ttk.Label(
                info_frame,
                text="⚠️ 脚本文件不存在",
                foreground="red"
            )
            missing_label.pack(anchor=tk.W)

    def launch_system(self, system):
        """启动指定的监控系统"""
        try:
            script_path = system["script"]

            if not os.path.exists(script_path):
                messagebox.showerror("错误", f"脚本文件不存在: {script_path}")
                return

            print(f"🚀 启动 {system['name']}")
            print(f"   脚本: {script_path}")

            # 根据脚本类型选择启动方式
            if "web" in script_path.lower():
                # Web系统在新窗口启动
                subprocess.Popen([sys.executable, script_path])
                messagebox.showinfo(
                    "Web系统启动",
                    "Web监控系统已启动！\n请打开浏览器访问: http://localhost:5000"
                )
            else:
                # 桌面系统直接启动
                subprocess.Popen([sys.executable, script_path])
                messagebox.showinfo(
                    "系统启动",
                    f"{system['name']} 已启动！"
                )

        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动系统: {str(e)}")

    def check_dependencies(self):
        """检查依赖"""
        required_packages = [
            "cv2", "torch", "transformers", "qwen_vl_utils",
            "flask", "matplotlib", "pandas", "PIL", "numpy"
        ]

        missing_packages = []
        available_packages = []

        for package in required_packages:
            try:
                if package == "cv2":
                    import cv2
                elif package == "PIL":
                    from PIL import Image
                else:
                    importlib.import_module(package)
                available_packages.append(package)
            except ImportError:
                missing_packages.append(package)

        # 显示结果
        result_text = "📋 依赖检查结果:\n\n"

        if available_packages:
            result_text += "✅ 已安装的包:\n"
            for pkg in available_packages:
                result_text += f"   • {pkg}\n"
            result_text += "\n"

        if missing_packages:
            result_text += "❌ 缺失的包:\n"
            for pkg in missing_packages:
                result_text += f"   • {pkg}\n"
            result_text += "\n"
            result_text += "请使用 '安装依赖' 按钮或手动安装缺失的包。"
        else:
            result_text += "🎉 所有依赖都已安装！"

        messagebox.showinfo("依赖检查", result_text)

    def install_dependencies(self):
        """安装依赖"""
        install_commands = [
            "pip install opencv-python",
            "pip install torch torchvision torchaudio",
            "pip install transformers",
            "pip install flask",
            "pip install matplotlib pandas",
            "pip install Pillow numpy",
            "pip install qwen_vl_utils"
        ]

        result = messagebox.askyesno(
            "安装依赖",
            "即将安装以下依赖包:\n\n" +
            "\n".join([cmd.replace("pip install ", "• ") for cmd in install_commands]) +
            "\n\n是否继续？"
        )

        if result:
            try:
                print("📦 开始安装依赖...")

                for cmd in install_commands:
                    print(f"执行: {cmd}")
                    subprocess.run(cmd.split(), check=True,
                                 capture_output=True, text=True)

                messagebox.showinfo("安装完成", "所有依赖已成功安装！")

            except subprocess.CalledProcessError as e:
                messagebox.showerror(
                    "安装失败",
                    f"依赖安装失败:\n{e.stderr}\n\n请手动安装或检查网络连接。"
                )
            except Exception as e:
                messagebox.showerror("错误", f"安装过程中出现错误: {str(e)}")

    def run(self):
        """运行启动器"""
        self.root.mainloop()

def main():
    """主函数"""
    print("🎥 监控系统启动器")
    print("=" * 30)

    launcher = MonitoringLauncher()
    launcher.run()

if __name__ == "__main__":
    main()