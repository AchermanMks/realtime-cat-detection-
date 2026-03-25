#!/usr/bin/env python3
"""
VLM配置测试脚本
测试不同的模型配置和参数设置
"""
import torch
import time
import os
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

def test_config(config_name, model_kwargs, generation_kwargs, image_path="test.jpg"):
    """测试特定配置"""
    print(f"\n{'='*50}")
    print(f"测试配置: {config_name}")
    print(f"{'='*50}")

    model_id = "Qwen/Qwen2-VL-7B-Instruct"

    # 加载模型
    load_start = time.time()
    try:
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id,
            **model_kwargs
        )
        processor = AutoProcessor.from_pretrained(model_id)
        load_time = time.time() - load_start
        print(f"✓ 模型加载成功，耗时: {load_time:.2f}秒")
    except Exception as e:
        print(f"✗ 模型加载失败: {e}")
        return None

    # 准备输入
    if not os.path.exists(image_path):
        print(f"✗ 图像文件 {image_path} 不存在")
        return None

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": "请简要描述这张图片。"},
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
    ).to("cuda" if torch.cuda.is_available() else "cpu")
    prep_time = time.time() - prep_start

    # 推理
    gen_start = time.time()
    try:
        if torch.cuda.is_available():
            memory_before = torch.cuda.memory_allocated() / 1e9

        generated_ids = model.generate(**inputs, **generation_kwargs)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )

        gen_time = time.time() - gen_start

        if torch.cuda.is_available():
            memory_after = torch.cuda.memory_allocated() / 1e9

        output_tokens = len(generated_ids_trimmed[0])
        tokens_per_sec = output_tokens / gen_time if gen_time > 0 else 0

        result = {
            'config_name': config_name,
            'load_time': load_time,
            'prep_time': prep_time,
            'gen_time': gen_time,
            'output_tokens': output_tokens,
            'tokens_per_sec': tokens_per_sec,
            'memory_usage': memory_after if torch.cuda.is_available() else 0,
            'response': output_text[0],
            'success': True
        }

        print(f"✓ 推理成功")
        print(f"  - 预处理: {prep_time:.2f}秒")
        print(f"  - 生成: {gen_time:.2f}秒")
        print(f"  - 速度: {tokens_per_sec:.1f} tokens/秒")
        if torch.cuda.is_available():
            print(f"  - 显存: {memory_after:.2f}GB")
        print(f"  - 回复: {output_text[0][:80]}...")

        return result

    except Exception as e:
        gen_time = time.time() - gen_start
        print(f"✗ 推理失败: {e}")
        return {
            'config_name': config_name,
            'load_time': load_time,
            'prep_time': prep_time,
            'gen_time': gen_time,
            'success': False,
            'error': str(e)
        }

def main():
    """主函数"""
    print("VLM配置对比测试")
    print(f"CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"设备: {torch.cuda.get_device_name()}")

    # 不同的配置
    configs = [
        {
            'name': '默认配置',
            'model_kwargs': {
                'torch_dtype': 'auto',
                'device_map': 'auto',
            },
            'generation_kwargs': {
                'max_new_tokens': 256,
            }
        },
        {
            'name': '高精度配置',
            'model_kwargs': {
                'torch_dtype': torch.float32,
                'device_map': 'auto',
            },
            'generation_kwargs': {
                'max_new_tokens': 256,
                'do_sample': False,
            }
        },
        {
            'name': '采样生成',
            'model_kwargs': {
                'torch_dtype': 'auto',
                'device_map': 'auto',
            },
            'generation_kwargs': {
                'max_new_tokens': 256,
                'do_sample': True,
                'temperature': 0.7,
                'top_p': 0.8,
            }
        },
        {
            'name': '快速生成',
            'model_kwargs': {
                'torch_dtype': 'auto',
                'device_map': 'auto',
            },
            'generation_kwargs': {
                'max_new_tokens': 128,
                'do_sample': False,
                'num_beams': 1,
            }
        }
    ]

    results = []
    for config in configs:
        result = test_config(
            config['name'],
            config['model_kwargs'],
            config['generation_kwargs']
        )
        if result:
            results.append(result)

        # 清理显存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        time.sleep(2)  # 短暂休息

    # 输出对比结果
    print(f"\n{'='*60}")
    print("配置对比总结")
    print(f"{'='*60}")

    successful_results = [r for r in results if r.get('success', False)]

    if successful_results:
        print(f"{'配置名称':<15} {'加载(秒)':<8} {'生成(秒)':<8} {'速度(t/s)':<10} {'显存(GB)':<8}")
        print("-" * 60)
        for result in successful_results:
            print(f"{result['config_name']:<15} "
                  f"{result['load_time']:<8.2f} "
                  f"{result['gen_time']:<8.2f} "
                  f"{result['tokens_per_sec']:<10.1f} "
                  f"{result['memory_usage']:<8.1f}")

        # 找出最佳配置
        fastest = max(successful_results, key=lambda x: x['tokens_per_sec'])
        print(f"\n最快配置: {fastest['config_name']} ({fastest['tokens_per_sec']:.1f} tokens/秒)")

if __name__ == "__main__":
    main()