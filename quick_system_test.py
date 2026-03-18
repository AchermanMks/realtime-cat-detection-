#!/usr/bin/env python3
"""
快速系统测试
验证摄像头连接、模型加载等基本功能
"""

import cv2
import torch
import time
import sys
import os
from datetime import datetime

class SystemTester:
    """系统测试器"""

    def __init__(self):
        self.test_results = {}
        self.camera_urls = [
            "rtsp://192.168.31.146:8554/unicast",  # 主摄像头
            0,  # 默认USB摄像头
            1,  # 备用USB摄像头
        ]

    def print_header(self, title):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print('='*60)

    def print_result(self, test_name, success, details=""):
        """打印测试结果"""
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
        if details:
            print(f"   详情: {details}")

        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': time.time()
        }

    def test_python_environment(self):
        """测试Python环境"""
        self.print_header("Python环境测试")

        # Python版本
        python_version = sys.version.split()[0]
        print(f"Python版本: {python_version}")

        # 测试基础包
        packages_to_test = [
            ("OpenCV", "cv2"),
            ("PyTorch", "torch"),
            ("Transformers", "transformers"),
            ("NumPy", "numpy"),
            ("PIL", "PIL"),
            ("Flask", "flask"),
            ("Matplotlib", "matplotlib"),
            ("Pandas", "pandas"),
        ]

        all_packages_ok = True
        for package_name, import_name in packages_to_test:
            try:
                __import__(import_name)
                self.print_result(f"{package_name}包", True)
            except ImportError as e:
                self.print_result(f"{package_name}包", False, str(e))
                all_packages_ok = False

        self.print_result("Python环境", all_packages_ok)
        return all_packages_ok

    def test_cuda_support(self):
        """测试CUDA支持"""
        self.print_header("CUDA支持测试")

        try:
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0)
                memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9

                details = f"设备数量: {device_count}, 设备名称: {device_name}, 显存: {memory_gb:.1f}GB"
                self.print_result("CUDA支持", True, details)
            else:
                self.print_result("CUDA支持", False, "CUDA不可用，将使用CPU")

        except Exception as e:
            self.print_result("CUDA测试", False, str(e))

        return True  # CUDA不是必需的

    def test_camera_connections(self):
        """测试摄像头连接"""
        self.print_header("摄像头连接测试")

        working_cameras = []

        for i, camera_url in enumerate(self.camera_urls):
            camera_name = f"摄像头{i+1} ({camera_url})"

            try:
                print(f"测试 {camera_name}...")
                cap = cv2.VideoCapture(camera_url)

                # 设置较短的超时时间
                if isinstance(camera_url, str):  # RTSP摄像头
                    cap.set(cv2.CAP_PROP_TIMEOUT, 5000)  # 5秒超时

                # 尝试读取一帧
                ret, frame = cap.read()

                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    fps = cap.get(cv2.CAP_PROP_FPS)

                    details = f"分辨率: {w}x{h}, FPS: {fps:.1f}"
                    self.print_result(camera_name, True, details)
                    working_cameras.append((camera_url, w, h, fps))

                    # 保存测试帧
                    test_frame_path = f"test_frame_{i+1}_{int(time.time())}.jpg"
                    cv2.imwrite(test_frame_path, frame)
                    print(f"   测试帧已保存: {test_frame_path}")

                else:
                    self.print_result(camera_name, False, "无法获取视频帧")

                cap.release()

            except Exception as e:
                self.print_result(camera_name, False, str(e))

        if working_cameras:
            self.print_result("摄像头连接", True, f"找到{len(working_cameras)}个可用摄像头")
            return True
        else:
            self.print_result("摄像头连接", False, "没有可用的摄像头")
            return False

    def test_vlm_model_loading(self):
        """测试VLM模型加载（可选）"""
        self.print_header("VLM模型测试")

        print("⚠️  注意: VLM模型测试需要较长时间和大量内存/显存")
        user_input = input("是否进行VLM模型测试? (y/n): ").lower().strip()

        if user_input != 'y':
            self.print_result("VLM模型测试", True, "用户跳过")
            return True

        try:
            print("正在加载VLM模型...")
            start_time = time.time()

            # 尝试加载模型
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

            model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-7B-Instruct",
                torch_dtype="auto",
                device_map="auto",
            )
            processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

            load_time = time.time() - start_time
            details = f"加载耗时: {load_time:.2f}秒"
            self.print_result("VLM模型加载", True, details)

            # 清理内存
            del model, processor
            torch.cuda.empty_cache() if torch.cuda.is_available() else None

            return True

        except Exception as e:
            self.print_result("VLM模型加载", False, str(e))
            return False

    def test_file_permissions(self):
        """测试文件权限"""
        self.print_header("文件权限测试")

        # 测试临时文件写入
        try:
            test_file = "/tmp/system_test.txt"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            self.print_result("临时文件写入", True)
        except Exception as e:
            self.print_result("临时文件写入", False, str(e))

        # 测试当前目录写入
        try:
            test_file = "system_test.txt"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            self.print_result("当前目录写入", True)
        except Exception as e:
            self.print_result("当前目录写入", False, str(e))

        return True

    def test_network_connectivity(self):
        """测试网络连接"""
        self.print_header("网络连接测试")

        import socket

        # 测试互联网连接
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self.print_result("互联网连接", True)
        except Exception:
            self.print_result("互联网连接", False, "无法连接到外部网络")

        # 测试本地网络
        try:
            # 尝试连接到摄像头IP
            rtsp_url = "rtsp://192.168.31.146:8554/unicast"
            host = "192.168.31.146"
            port = 8554

            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            self.print_result("RTSP摄像头网络", True, f"可以连接到 {host}:{port}")
        except Exception as e:
            self.print_result("RTSP摄像头网络", False, f"无法连接到摄像头: {str(e)}")

        return True

    def generate_report(self):
        """生成测试报告"""
        self.print_header("测试报告")

        # 统计结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests

        print(f"📊 测试统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过: {passed_tests}")
        print(f"   失败: {failed_tests}")
        print(f"   成功率: {passed_tests/total_tests*100:.1f}%")

        # 详细结果
        print(f"\n📋 详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {test_name}")
            if result['details']:
                print(f"       {result['details']}")

        # 建议
        print(f"\n💡 建议:")
        if failed_tests == 0:
            print("   🎉 所有测试都通过了！系统已准备就绪。")
        else:
            print("   🔧 请解决失败的测试项目后再运行监控系统。")

        # 保存报告
        report_file = f"system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"系统测试报告 - {datetime.now()}\n")
                f.write("="*50 + "\n\n")
                f.write(f"总测试数: {total_tests}\n")
                f.write(f"通过: {passed_tests}\n")
                f.write(f"失败: {failed_tests}\n")
                f.write(f"成功率: {passed_tests/total_tests*100:.1f}%\n\n")

                for test_name, result in self.test_results.items():
                    status = "通过" if result['success'] else "失败"
                    f.write(f"{test_name}: {status}\n")
                    if result['details']:
                        f.write(f"  详情: {result['details']}\n")

            print(f"\n📄 详细报告已保存到: {report_file}")

        except Exception as e:
            print(f"⚠️  无法保存报告: {e}")

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始系统测试")
        print(f"时间: {datetime.now()}")

        # 执行所有测试
        tests = [
            self.test_python_environment,
            self.test_cuda_support,
            self.test_file_permissions,
            self.test_network_connectivity,
            self.test_camera_connections,
            self.test_vlm_model_loading,
        ]

        for test_func in tests:
            try:
                test_func()
            except KeyboardInterrupt:
                print("\n⚠️  测试被用户中断")
                break
            except Exception as e:
                print(f"❌ 测试异常: {e}")

        # 生成报告
        self.generate_report()

def main():
    """主函数"""
    tester = SystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()