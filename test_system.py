#!/usr/bin/env python3
"""
机器人视觉系统快速测试脚本
"""

import sys
import time

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")

    try:
        import torch
        print(f"✅ PyTorch {torch.__version__}")

        import cv2
        print(f"✅ OpenCV {cv2.__version__}")

        import transformers
        print(f"✅ Transformers {transformers.__version__}")

        import requests
        print("✅ Requests")

        from robot_vision_config import Config
        print("✅ 配置模块")

        from rtsp_streamer import RTSPStreamer
        print("✅ RTSP流模块")

        from vision_analyzer import VisionAnalyzer
        print("✅ 视觉分析模块")

        from ptz_controller import PTZController
        print("✅ 云台控制模块")

        return True

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_cuda():
    """测试CUDA环境"""
    print("\n🔥 测试CUDA环境...")

    try:
        import torch

        if torch.cuda.is_available():
            print(f"✅ CUDA可用")
            print(f"   设备: {torch.cuda.get_device_name()}")
            print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            return True
        else:
            print("⚠️ CUDA不可用，将使用CPU模式")
            return False

    except Exception as e:
        print(f"❌ CUDA测试失败: {e}")
        return False

def test_config():
    """测试配置"""
    print("\n⚙️ 测试配置...")

    try:
        from robot_vision_config import Config
        Config.validate()

        print(f"✅ RTSP URL: {Config.RTSP_URL[:30]}...")
        print(f"✅ 模型ID: {Config.MODEL_ID}")
        print(f"✅ 分析间隔: {Config.ANALYSIS_INTERVAL}秒")
        print(f"✅ 自动跟踪: {Config.AUTO_TRACKING}")

        return True

    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_model_loading():
    """测试模型加载(可选)"""
    print("\n🤖 测试模型加载...")

    choice = input("是否测试VLM模型加载? (需要下载约15GB模型) [y/N]: ")

    if choice.lower() != 'y':
        print("⏭️ 跳过模型加载测试")
        return True

    try:
        from vision_analyzer import VisionAnalyzer

        analyzer = VisionAnalyzer()
        print("正在加载模型，请稍候...")

        if analyzer.load_model():
            print("✅ 模型加载成功")
            return True
        else:
            print("❌ 模型加载失败")
            return False

    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        return False

def test_rtsp_connection():
    """测试RTSP连接"""
    print("\n📡 测试RTSP连接...")

    choice = input("是否测试RTSP连接? (需要摄像头在线) [y/N]: ")

    if choice.lower() != 'y':
        print("⏭️ 跳过RTSP连接测试")
        return True

    try:
        from rtsp_streamer import RTSPStreamer

        # 允许用户输入自定义RTSP地址
        custom_url = input("输入RTSP地址 (回车使用默认): ").strip()

        streamer = RTSPStreamer(custom_url if custom_url else None)

        if streamer.test_stream(5):
            print("✅ RTSP连接测试成功")
            return True
        else:
            print("❌ RTSP连接测试失败")
            return False

    except Exception as e:
        print(f"❌ RTSP测试失败: {e}")
        return False

def test_ptz_connection():
    """测试云台连接"""
    print("\n🎮 测试云台连接...")

    choice = input("是否测试云台连接? (需要云台在线) [y/N]: ")

    if choice.lower() != 'y':
        print("⏭️ 跳过云台连接测试")
        return True

    try:
        from ptz_controller import PTZController

        ptz = PTZController()

        if ptz.test_connection():
            print("✅ 云台连接测试成功")
            return True
        else:
            print("❌ 云台连接测试失败")
            return False

    except Exception as e:
        print(f"❌ 云台测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🤖 机器人视觉系统测试")
    print("=" * 40)

    tests = [
        test_imports,
        test_cuda,
        test_config,
        test_model_loading,
        test_rtsp_connection,
        test_ptz_connection
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except KeyboardInterrupt:
            print("\n❌ 用户中断测试")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 测试异常: {e}")

    print("\n" + "=" * 40)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！系统准备就绪")
        print("\n🚀 运行系统:")
        print("   ./start_robot_vision.sh")
        print("   或")
        print("   python3 robot_vision_main.py")
    else:
        print("⚠️ 部分测试失败，请检查配置")

    print("=" * 40)

if __name__ == "__main__":
    main()