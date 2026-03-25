#!/usr/bin/env python3
"""
测试VLM模型 - 使用静态图片
"""

import cv2
import torch
import numpy as np
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import time

def create_test_image():
    """创建测试图片"""
    img = np.zeros((480, 640, 3), dtype=np.uint8)

    # 添加渐变背景
    for y in range(480):
        for x in range(640):
            img[y, x] = [int(x * 255 / 640), int(y * 255 / 480), 128]

    # 添加文字和图形
    cv2.rectangle(img, (50, 50), (590, 430), (255, 255, 255), 2)
    cv2.putText(img, "VLM Test Image", (200, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    cv2.putText(img, "Testing AI Vision Analysis", (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # 添加几何图形
    cv2.circle(img, (320, 350), 50, (0, 255, 0), -1)  # 绿色圆
    cv2.rectangle(img, (200, 300), (300, 400), (255, 0, 0), 3)  # 蓝色矩形

    return img

def test_vlm():
    """测试VLM模型"""
    print("🤖 加载VLM模型...")

    # 加载模型
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-7B-Instruct",
        torch_dtype="auto",
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")

    print("✅ 模型加载完成")

    # 创建测试图片
    print("📸 创建测试图片...")
    test_img = create_test_image()

    # 保存图片
    test_path = "/tmp/vlm_test.jpg"
    cv2.imwrite(test_path, test_img)
    print(f"💾 测试图片保存到: {test_path}")

    # 分析图片
    print("🔍 开始AI分析...")
    start_time = time.time()

    # 构建消息
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": test_path},
                {"type": "text", "text": "详细描述这张图片的内容，包括文字、颜色、形状等所有可见元素。"},
            ],
        }
    ]

    # VLM处理
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to("cuda" if torch.cuda.is_available() else "cpu")

    generated_ids = model.generate(**inputs, max_new_tokens=200)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    analysis_time = time.time() - start_time

    print(f"✅ 分析完成 (耗时: {analysis_time:.2f}秒)")
    print("=" * 50)
    print("🤖 AI分析结果:")
    print(output_text.strip())
    print("=" * 50)

if __name__ == "__main__":
    test_vlm()