import torch
import time
import cv2
import numpy as np
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from robot_vision_config import Config
import threading
import queue
import json
import re

class VisionAnalyzer:
    """视觉分析器，使用VLM模型进行实时分析"""

    def __init__(self):
        self.model = None
        self.processor = None
        self.analysis_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue(maxsize=50)
        self.analyzing = False
        self.analysis_thread = None
        self.last_analysis_time = 0

        print("初始化视觉分析器...")

    def load_model(self):
        """加载VLM模型"""
        try:
            print(f"正在加载模型: {Config.MODEL_ID}")
            start_time = time.time()

            # 检查CUDA可用性
            if torch.cuda.is_available():
                print(f"✅ CUDA设备: {torch.cuda.get_device_name()}")
                print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            else:
                print("⚠️ CUDA不可用，将使用CPU")

            # 加载模型
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                Config.MODEL_ID,
                torch_dtype=Config.TORCH_DTYPE,
                device_map=Config.DEVICE_MAP,
            )

            # 加载处理器
            self.processor = AutoProcessor.from_pretrained(Config.MODEL_ID)

            load_time = time.time() - start_time
            print(f"✅ 模型加载完成，耗时: {load_time:.2f}秒")

            return True

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False

    def start_analysis(self):
        """开始视觉分析线程"""
        if not self.model or not self.processor:
            print("❌ 模型未加载，无法开始分析")
            return False

        self.analyzing = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        print("🔍 开始视觉分析")
        return True

    def stop_analysis(self):
        """停止视觉分析"""
        print("停止视觉分析...")
        self.analyzing = False

        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)

        # 清空队列
        while not self.analysis_queue.empty():
            try:
                self.analysis_queue.get_nowait()
            except queue.Empty:
                break

        print("✅ 视觉分析已停止")

    def analyze_frame(self, frame, prompt=None):
        """分析单帧图像"""
        current_time = time.time()

        # 控制分析频率
        if current_time - self.last_analysis_time < Config.ANALYSIS_INTERVAL:
            return None

        if self.analysis_queue.full():
            return None  # 队列满时跳过

        # 默认提示词
        if prompt is None:
            prompt = """请分析这个图像并回答：
1. 图像中有哪些主要物体？
2. 是否检测到人、车辆或其他重要目标？
3. 如果有人，请描述他们在做什么？
4. 场景的整体环境如何？

请以JSON格式回复：
{
    "objects": ["物体1", "物体2"],
    "persons": [{"action": "动作描述", "location": "位置"}],
    "vehicles": ["车辆类型"],
    "scene": "场景描述",
    "priority_target": "最重要的目标",
    "tracking_suggestion": "跟踪建议"
}"""

        try:
            # 将帧和提示加入分析队列
            analysis_request = {
                "frame": frame.copy(),
                "prompt": prompt,
                "timestamp": current_time
            }

            self.analysis_queue.put_nowait(analysis_request)
            self.last_analysis_time = current_time
            return True

        except queue.Full:
            return None
        except Exception as e:
            print(f"分析帧时出错: {e}")
            return None

    def _analysis_loop(self):
        """内部分析循环"""
        while self.analyzing:
            try:
                # 获取分析请求
                request = self.analysis_queue.get(timeout=1)

                if request is None:
                    continue

                frame = request["frame"]
                prompt = request["prompt"]
                timestamp = request["timestamp"]

                print(f"🔍 开始分析帧 (时间戳: {timestamp:.2f})")

                # 执行VLM分析
                start_time = time.time()
                result = self._run_vlm_analysis(frame, prompt)
                analysis_time = time.time() - start_time

                if result:
                    result["timestamp"] = timestamp
                    result["analysis_time"] = analysis_time

                    # 将结果放入结果队列
                    if not self.result_queue.full():
                        self.result_queue.put(result)
                    else:
                        # 队列满时，移除最旧的结果
                        try:
                            self.result_queue.get_nowait()
                            self.result_queue.put(result)
                        except queue.Empty:
                            pass

                    print(f"✅ 分析完成，耗时: {analysis_time:.2f}秒")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"分析循环异常: {e}")

    def _run_vlm_analysis(self, frame, prompt):
        """执行VLM模型分析"""
        try:
            # 保存临时图片
            temp_path = "/tmp/temp_frame.jpg"
            cv2.imwrite(temp_path, frame)

            # 构建消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": temp_path},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            # 处理输入
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to("cuda" if torch.cuda.is_available() else "cpu")

            # 生成回复
            generated_ids = self.model.generate(**inputs, max_new_tokens=512)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]

            # 解析结果
            parsed_result = self._parse_analysis_result(output_text, frame)

            return parsed_result

        except Exception as e:
            print(f"VLM分析异常: {e}")
            return None

    def _parse_analysis_result(self, output_text, frame):
        """解析VLM分析结果"""
        try:
            # 尝试提取JSON格式的回复
            json_match = re.search(r'\{.*\}', output_text, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group())
                    result = {
                        "raw_text": output_text,
                        "parsed_data": parsed_json,
                        "objects": parsed_json.get("objects", []),
                        "persons": parsed_json.get("persons", []),
                        "vehicles": parsed_json.get("vehicles", []),
                        "scene": parsed_json.get("scene", ""),
                        "priority_target": parsed_json.get("priority_target", ""),
                        "tracking_suggestion": parsed_json.get("tracking_suggestion", ""),
                        "frame_shape": frame.shape
                    }
                    return result
                except json.JSONDecodeError:
                    pass

            # 如果无法解析JSON，则进行简单的文本分析
            result = {
                "raw_text": output_text,
                "parsed_data": None,
                "objects": self._extract_objects_from_text(output_text),
                "persons": [],
                "vehicles": [],
                "scene": output_text[:200] + "..." if len(output_text) > 200 else output_text,
                "priority_target": "",
                "tracking_suggestion": "",
                "frame_shape": frame.shape
            }

            return result

        except Exception as e:
            print(f"解析分析结果时出错: {e}")
            return {
                "raw_text": output_text,
                "parsed_data": None,
                "objects": [],
                "persons": [],
                "vehicles": [],
                "scene": "",
                "priority_target": "",
                "tracking_suggestion": "",
                "frame_shape": frame.shape,
                "error": str(e)
            }

    def _extract_objects_from_text(self, text):
        """从文本中提取对象信息"""
        common_objects = ["人", "车", "自行车", "摩托车", "狗", "猫", "椅子", "桌子", "电脑", "手机"]
        detected_objects = []

        for obj in common_objects:
            if obj in text:
                detected_objects.append(obj)

        return detected_objects

    def get_latest_result(self):
        """获取最新的分析结果"""
        try:
            latest_result = None
            while not self.result_queue.empty():
                try:
                    latest_result = self.result_queue.get_nowait()
                except queue.Empty:
                    break
            return latest_result
        except Exception as e:
            print(f"获取分析结果时出错: {e}")
            return None

    def get_analysis_stats(self):
        """获取分析统计信息"""
        return {
            "analyzing": self.analyzing,
            "analysis_queue_size": self.analysis_queue.qsize(),
            "result_queue_size": self.result_queue.qsize(),
            "model_loaded": self.model is not None,
            "last_analysis_time": self.last_analysis_time
        }