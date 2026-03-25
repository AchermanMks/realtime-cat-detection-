#!/usr/bin/env python3
"""
命令行版监控系统启动器
适用于没有图形界面的环境
"""

import sys
import os
import subprocess
import time

class CLIMonitoringLauncher:
    """命令行监控系统启动器"""

    def __init__(self):
        self.systems = [
            {
                "id": "1",
                "name": "桌面版实时监控",
                "description": "基于OpenCV的桌面监控界面，支持快捷键操作",
                "script": "realtime_camera_display.py",
                "features": ["实时视频显示", "VLM分析", "快捷键控制", "截图功能"],
                "requires_display": True
            },
            {
                "id": "2",
                "name": "Web版监控界面",
                "description": "基于Flask的Web监控，通过浏览器访问",
                "script": "web_camera_stream.py",
                "features": ["Web界面", "远程访问", "实时统计", "移动端兼容"],
                "requires_display": False
            },
            {
                "id": "3",
                "name": "高级监控仪表板",
                "description": "功能最完整的监控系统，包含数据分析和报警",
                "script": "advanced_monitoring_dashboard.py",
                "features": ["GUI仪表板", "数据库存储", "报警系统", "统计分析", "数据导出"],
                "requires_display": True
            },
            {
                "id": "4",
                "name": "简单VLM测试",
                "description": "轻量级摄像头VLM测试工具",
                "script": "simple_camera_vlm.py",
                "features": ["轻量级", "快速测试", "基础分析"],
                "requires_display": False
            },
            {
                "id": "5",
                "name": "虚拟摄像头演示",
                "description": "使用虚拟数据的完整功能演示",
                "script": "demo_monitoring_system.py",
                "features": ["虚拟摄像头", "完整演示", "无需硬件"],
                "requires_display": True
            },
            {
                "id": "6",
                "name": "文本版演示",
                "description": "纯命令行的功能演示",
                "script": "auto_demo.py",
                "features": ["命令行界面", "无需GUI", "快速演示"],
                "requires_display": False
            }
        ]

    def print_header(self):
        """打印标题"""
        print("=" * 60)
        print("🎥 监控系统启动器 (命令行版)")
        print("=" * 60)

    def print_systems(self):
        """显示可用系统"""
        print("\n📋 可用监控系统:")
        print("-" * 40)

        for system in self.systems:
            status = "🟢" if not system["requires_display"] else "🟡" if self.check_display() else "🔴"
            print(f"{status} [{system['id']}] {system['name']}")
            print(f"    📝 {system['description']}")
            print(f"    ✨ 特性: {', '.join(system['features'])}")

            if system["requires_display"] and not self.check_display():
                print(f"    ⚠️  需要图形界面环境")

            if not os.path.exists(system["script"]):
                print(f"    ❌ 脚本文件不存在: {system['script']}")
            else:
                print(f"    ✅ 就绪")
            print()

    def check_display(self):
        """检查是否有图形显示环境"""
        return os.environ.get('DISPLAY') is not None

    def check_dependencies(self):
        """检查依赖"""
        print("\n🔍 检查依赖...")

        required_packages = [
            ("OpenCV", "cv2"),
            ("PyTorch", "torch"),
            ("Transformers", "transformers"),
            ("Flask", "flask"),
            ("NumPy", "numpy"),
            ("Pandas", "pandas")
        ]

        missing_packages = []
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                print(f"✅ {package_name}")
            except ImportError:
                print(f"❌ {package_name} (缺失)")
                missing_packages.append(package_name)

        if missing_packages:
            print(f"\n⚠️  缺失依赖: {', '.join(missing_packages)}")
            print("建议运行: pip install opencv-python torch transformers flask numpy pandas")
        else:
            print("\n✅ 所有依赖都已安装")

        return len(missing_packages) == 0

    def launch_system(self, system_id):
        """启动指定系统"""
        system = None
        for sys in self.systems:
            if sys["id"] == system_id:
                system = sys
                break

        if not system:
            print(f"❌ 无效的系统ID: {system_id}")
            return False

        if not os.path.exists(system["script"]):
            print(f"❌ 脚本文件不存在: {system['script']}")
            return False

        if system["requires_display"] and not self.check_display():
            print(f"⚠️  {system['name']} 需要图形界面环境")
            print("建议:")
            print("  1. 使用远程桌面或X11转发")
            print("  2. 选择不需要GUI的选项 (如Web版)")
            return False

        try:
            print(f"🚀 启动 {system['name']}...")
            print(f"   脚本: {system['script']}")

            if "web" in system['script'].lower():
                print("\n📝 Web系统启动说明:")
                print("   • 系统将在后台启动Web服务器")
                print("   • 请打开浏览器访问: http://localhost:5000")
                print("   • 按 Ctrl+C 停止服务")

            # 启动系统
            python_exe = sys.executable or 'python3'
            if system['script'] == 'auto_demo.py':
                # 直接运行演示
                subprocess.run([python_exe, system['script']])
            else:
                # 在新进程中启动
                process = subprocess.Popen([python_exe, system['script']])

                if "web" in system['script'].lower():
                    print(f"\n✅ Web服务已启动 (PID: {process.pid})")
                    print("🌐 访问地址: http://localhost:5000")
                else:
                    print(f"\n✅ 系统已启动 (PID: {process.pid})")

            return True

        except Exception as e:
            print(f"❌ 启动失败: {str(e)}")
            return False

    def show_help(self):
        """显示帮助信息"""
        print("\n📖 使用说明:")
        print("  python3 cli_launcher.py [选项] [系统ID]")
        print("\n可用选项:")
        print("  -h, --help     显示此帮助信息")
        print("  -l, --list     列出所有可用系统")
        print("  -c, --check    检查依赖安装状态")
        print("  -d, --demo     直接运行文本演示")
        print("\n系统ID:")
        for system in self.systems:
            print(f"  {system['id']}  {system['name']}")
        print("\n示例:")
        print("  python3 cli_launcher.py -l          # 列出系统")
        print("  python3 cli_launcher.py 2           # 启动Web版监控")
        print("  python3 cli_launcher.py -d          # 运行演示")

    def interactive_mode(self):
        """交互模式"""
        self.print_header()

        print("🌟 欢迎使用监控系统启动器！")
        self.print_systems()

        while True:
            try:
                choice = input("\n请选择系统 (输入数字ID，h=帮助，c=检查依赖，q=退出): ").strip().lower()

                if choice == 'q':
                    print("👋 再见！")
                    break
                elif choice == 'h':
                    self.show_help()
                elif choice == 'c':
                    self.check_dependencies()
                elif choice in [sys["id"] for sys in self.systems]:
                    if self.launch_system(choice):
                        print("按任意键继续...")
                        input()
                else:
                    print("❌ 无效选择，请重试")

            except KeyboardInterrupt:
                print("\n\n👋 再见！")
                break
            except EOFError:
                print("\n\n👋 再见！")
                break

    def run(self):
        """运行启动器"""
        args = sys.argv[1:]

        if len(args) == 0:
            # 交互模式
            self.interactive_mode()
        elif args[0] in ['-h', '--help']:
            self.show_help()
        elif args[0] in ['-l', '--list']:
            self.print_header()
            self.print_systems()
        elif args[0] in ['-c', '--check']:
            self.print_header()
            self.check_dependencies()
        elif args[0] in ['-d', '--demo']:
            self.launch_system('6')  # 文本演示
        elif args[0] in [sys["id"] for sys in self.systems]:
            self.print_header()
            self.launch_system(args[0])
        else:
            print("❌ 无效参数")
            self.show_help()

def main():
    """主函数"""
    launcher = CLIMonitoringLauncher()
    launcher.run()

if __name__ == "__main__":
    main()