#!/usr/bin/env python3
"""
批量VLM测试脚本
支持测试多张图片和不同的提示词
"""
import torch
import time
import os
import glob
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

def load_model():
    """加载VLM模型"""
    print("=== 初始化模型 ===")
    start_time = time.time()
    model_id = "Qwen/Qwen2-VL-7B-Instruct"

    if torch.cuda.is_available():
        print(f"CUDA设备: {torch.cuda.get_device_name()}")
        print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("警告: CUDA不可用，将使用CPU")

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype="auto",
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(model_id)
    load_time = time.time() - start_time
    print(f"模型加载耗时: {load_time:.2f}秒")
    return model, processor, load_time

def test_image(model, processor, image_path, prompt="描述一下这张图，并列出图中的主要物体。"):
    """测试单张图片"""
    print(f"\n=== 测试图片: {image_path} ===")

    if not os.path.exists(image_path):
        print(f"错误: 图像文件 {image_path} 不存在")
        return None

    file_size = os.path.getsize(image_path) / 1024
    print(f"文件大小: {file_size:.1f} KB")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    # 数据预处理
    prep_start = time.time()
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to("cuda")
    prep_time = time.time() - prep_start

    input_tokens = inputs.input_ids.shape[1]
    print(f"输入tokens: {input_tokens}, 预处理耗时: {prep_time:.2f}秒")

    # 推理生成
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        memory_before = torch.cuda.memory_allocated() / 1e9

    gen_start = time.time()
    generated_ids = model.generate(**inputs, max_new_tokens=512)
    gen_time = time.time() - gen_start

    if torch.cuda.is_available():
        memory_after = torch.cuda.memory_allocated() / 1e9
        print(f"显存使用: {memory_after:.2f} GB")

    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )

    output_tokens = len(generated_ids_trimmed[0])
    tokens_per_sec = output_tokens / gen_time if gen_time > 0 else 0

    result = {
        'image_path': image_path,
        'file_size_kb': file_size,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'prep_time': prep_time,
        'gen_time': gen_time,
        'tokens_per_sec': tokens_per_sec,
        'response': output_text[0]
    }

    print(f"推理耗时: {gen_time:.2f}秒")
    print(f"生成速度: {tokens_per_sec:.1f} tokens/秒")
    print(f"回复: {output_text[0][:100]}...")

    return result

def main():
    """主函数"""
    model, processor, load_time = load_model()

    # 查找所有图片文件
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(ext))
        image_files.extend(glob.glob(ext.upper()))

    if not image_files:
        print("未找到图片文件，请确保当前目录有图片文件")
        return

    print(f"\n找到 {len(image_files)} 张图片")

    # 测试不同的提示词
    prompts = [
        "描述一下这张图，并列出图中的主要物体。",
        "这张图片的主题是什么？请详细分析。",
        "请识别图片中的文字内容。",
        "这张图片可能是在什么场景下拍摄的？"
    ]

    results = []
    for i, image_file in enumerate(image_files[:3]):  # 限制测试前3张图片
        for j, prompt in enumerate(prompts[:2]):  # 每张图片测试前2个提示词
            result = test_image(model, processor, image_file, prompt)
            if result:
                result['prompt_id'] = j
                result['prompt'] = prompt
                results.append(result)

    # 输出总结
    print(f"\n=== 批量测试总结 ===")
    print(f"模型加载耗时: {load_time:.2f}秒")
    print(f"测试了 {len(results)} 个样本")

    if results:
        avg_gen_time = sum(r['gen_time'] for r in results) / len(results)
        avg_tokens_per_sec = sum(r['tokens_per_sec'] for r in results) / len(results)
        print(f"平均推理耗时: {avg_gen_time:.2f}秒")
        print(f"平均生成速度: {avg_tokens_per_sec:.1f} tokens/秒")

if __name__ == "__main__":
    main()