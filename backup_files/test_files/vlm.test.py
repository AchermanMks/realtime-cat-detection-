import torch
import time
import os
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

# 1. 加载模型与处理器
print("=== 初始化模型 ===")
start_time = time.time()
model_id = "Qwen/Qwen2-VL-7B-Instruct"

# 检查CUDA可用性
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

# 2. 准备多模态输入
print("\n=== 准备输入 ===")
video_path = "test.mp4"

# 检查视频文件
if not os.path.exists(video_path):
    raise FileNotFoundError(f"视频文件 {video_path} 不存在")

print(f"视频文件: {video_path}")
file_size = os.path.getsize(video_path) / (1024 * 1024)
print(f"文件大小: {file_size:.1f} MB")

messages = [
    {
        "role": "user",
        "content": [
            {"type": "video", "video": video_path},
            {"type": "text", "text": "请详细描述这个视频的内容，包括场景、人物动作、关键事件等。"},
        ],
    }
]

# 准备处理
print("准备输入数据...")
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
print(f"数据预处理耗时: {prep_time:.2f}秒")

# 显示输入tokens数量
input_tokens = inputs.input_ids.shape[1]
print(f"输入tokens数量: {input_tokens}")

# 3. 推理生成
print("\n=== 开始生成 ===")
if torch.cuda.is_available():
    torch.cuda.empty_cache()  # 清理显存
    memory_before = torch.cuda.memory_allocated() / 1e9
    print(f"生成前显存使用: {memory_before:.2f} GB")

gen_start = time.time()
generated_ids = model.generate(**inputs, max_new_tokens=512)
gen_time = time.time() - gen_start

if torch.cuda.is_available():
    memory_after = torch.cuda.memory_allocated() / 1e9
    print(f"生成后显存使用: {memory_after:.2f} GB")

generated_ids_trimmed = [
    out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
]
output_text = processor.batch_decode(
    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
)

# 生成统计
output_tokens = len(generated_ids_trimmed[0])
tokens_per_sec = output_tokens / gen_time if gen_time > 0 else 0

print(f"\n=== 生成统计 ===")
print(f"推理耗时: {gen_time:.2f}秒")
print(f"生成tokens: {output_tokens}")
print(f"生成速度: {tokens_per_sec:.1f} tokens/秒")
print(f"总耗时: {load_time + prep_time + gen_time:.2f}秒")

print(f"\n=== 模型回复 ===")
print(output_text[0])