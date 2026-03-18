#!/usr/bin/env python3
"""
交互式VLM测试脚本
允许用户输入自定义图片路径和提示词
"""
import torch
import time
import os
import glob
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

class VLMTester:
    def __init__(self):
        self.model = None
        self.processor = None
        self.load_time = 0

    def load_model(self):
        """加载模型"""
        if self.model is not None:
            print("模型已加载")
            return

        print("🚀 正在加载模型...")
        start_time = time.time()
        model_id = "Qwen/Qwen2-VL-7B-Instruct"

        if torch.cuda.is_available():
            print(f"💾 CUDA设备: {torch.cuda.get_device_name()}")
            print(f"💾 显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto",
        )
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.load_time = time.time() - start_time
        print(f"✅ 模型加载完成，耗时: {self.load_time:.2f}秒")

    def list_images(self):
        """列出当前目录的图片文件"""
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
        images = []
        for ext in extensions:
            images.extend(glob.glob(ext))
            images.extend(glob.glob(ext.upper()))
        return sorted(images)

    def test_image(self, image_path, prompt, config="fast"):
        """测试图片"""
        if not os.path.exists(image_path):
            print(f"❌ 错误: 图像文件 {image_path} 不存在")
            return None

        print(f"\n📸 测试图片: {image_path}")
        file_size = os.path.getsize(image_path) / 1024
        print(f"📊 文件大小: {file_size:.1f} KB")

        # 配置选择
        gen_configs = {
            "fast": {"max_new_tokens": 128, "do_sample": False},
            "quality": {"max_new_tokens": 512, "do_sample": False},
            "creative": {"max_new_tokens": 256, "do_sample": True, "temperature": 0.7, "top_p": 0.8}
        }

        gen_kwargs = gen_configs.get(config, gen_configs["fast"])

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        # 预处理
        prep_start = time.time()
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to("cuda")
        prep_time = time.time() - prep_start

        # 推理
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        gen_start = time.time()
        generated_ids = self.model.generate(**inputs, **gen_kwargs)
        gen_time = time.time() - gen_start

        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )

        output_tokens = len(generated_ids_trimmed[0])
        tokens_per_sec = output_tokens / gen_time if gen_time > 0 else 0

        print(f"⚡ 推理耗时: {gen_time:.2f}秒")
        print(f"🎯 生成速度: {tokens_per_sec:.1f} tokens/秒")
        print(f"🤖 模型回复:\n{'-'*50}")
        print(output_text[0])
        print(f"{'-'*50}")

        return output_text[0]

def main():
    """主函数"""
    tester = VLMTester()

    print("🎨 VLM交互式测试工具")
    print("="*50)

    while True:
        print("\n📋 可用命令:")
        print("1. load - 加载模型")
        print("2. list - 列出当前目录图片")
        print("3. test - 测试图片")
        print("4. quit - 退出")

        cmd = input("\n请输入命令: ").strip().lower()

        if cmd == 'quit' or cmd == 'q':
            print("👋 再见！")
            break

        elif cmd == 'load' or cmd == '1':
            tester.load_model()

        elif cmd == 'list' or cmd == '2':
            images = tester.list_images()
            if images:
                print("\n🖼️  发现的图片文件:")
                for i, img in enumerate(images, 1):
                    size = os.path.getsize(img) / 1024
                    print(f"{i:2d}. {img} ({size:.1f} KB)")
            else:
                print("❌ 当前目录没有找到图片文件")

        elif cmd == 'test' or cmd == '3':
            if tester.model is None:
                print("❌ 请先加载模型 (输入 'load')")
                continue

            # 选择图片
            images = tester.list_images()
            if not images:
                print("❌ 当前目录没有图片文件")
                continue

            print("\n🖼️  可用图片:")
            for i, img in enumerate(images, 1):
                print(f"{i}. {img}")

            try:
                choice = input("请选择图片编号 (或直接输入路径): ").strip()
                if choice.isdigit():
                    img_idx = int(choice) - 1
                    if 0 <= img_idx < len(images):
                        image_path = images[img_idx]
                    else:
                        print("❌ 无效的编号")
                        continue
                else:
                    image_path = choice

                # 输入提示词
                print("\n💭 输入提示词 (留空使用默认):")
                prompt = input("提示词: ").strip()
                if not prompt:
                    prompt = "请详细描述这张图片的内容。"

                # 选择配置
                print("\n⚙️  生成配置:")
                print("1. fast - 快速生成")
                print("2. quality - 高质量生成")
                print("3. creative - 创意生成")
                config_choice = input("选择配置 (默认fast): ").strip()
                config_map = {"1": "fast", "2": "quality", "3": "creative"}
                config = config_map.get(config_choice, "fast")

                tester.test_image(image_path, prompt, config)

            except ValueError:
                print("❌ 无效的输入")
            except KeyboardInterrupt:
                print("\n⏸️  操作已取消")

        else:
            print("❌ 未知命令，请重新输入")

if __name__ == "__main__":
    main()