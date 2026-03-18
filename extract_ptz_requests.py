#!/usr/bin/env python3
"""
PTZ请求信息提取指南
帮助用户从浏览器开发者工具中提取PTZ控制请求信息
"""

def create_extraction_guide():
    """创建提取指南"""

    guide = """
🔍 PTZ网络请求信息提取指南
==========================================

📋 在浏览器开发者工具(F12)中，请按以下步骤操作：

## 步骤1: 准备工作
1. 确保在 Network 标签页
2. 勾选 "Preserve log" (保留日志)
3. 清空当前请求列表
4. 准备操作PTZ控制

## 步骤2: 捕获PTZ请求
1. 在摄像头Web界面中操作PTZ控制 (点击方向按钮)
2. 观察Network标签页中出现的新请求
3. 寻找与PTZ相关的请求 (通常包含关键词如: ptz, move, control, motor等)

## 步骤3: 提取请求信息
对于每个PTZ相关请求，请提供以下信息：

### 基本信息:
- 请求URL (完整地址)
- 请求方法 (GET/POST/PUT等)
- 状态码 (200/404等)

### 请求详情:
- Request Headers (请求头)
- Request Payload/Form Data (如果有)
- Query Parameters (URL参数)

### 响应信息:
- Response Headers (响应头)
- Response Body (响应内容)

## 📝 信息收集模板
请将发现的信息按以下格式提供：

```
=== PTZ请求 #1 ===
操作: 向左移动
URL: https://192.168.31.146/xxxxx
方法: GET/POST
状态码: 200

请求参数:
- 参数1: 值1
- 参数2: 值2

请求头:
Content-Type: application/json
...

请求体 (如果是POST):
{"action": "move", "direction": "left"}

响应头:
Content-Type: text/html
...

响应内容:
{"status": "ok", "result": "success"}

=== PTZ请求 #2 ===
操作: 向右移动
...
```

## 🎯 重点关注的请求特征
寻找以下特征的请求:
- URL包含: ptz, motor, move, control, cgi-bin
- 请求发生在点击PTZ控制按钮时
- 状态码为200的成功请求
- 响应内容不是404错误页面

## 💡 提示
- 可以右键点击请求选择 "Copy as cURL" 获取完整命令
- 可以在 Headers 标签查看详细信息
- 可以在 Payload 标签查看POST数据
- 可以在 Response 标签查看返回内容
"""

    return guide

def create_request_template():
    """创建请求信息模板文件"""

    template = """
# PTZ请求信息收集模板
# 请填写在浏览器开发者工具中发现的PTZ请求信息

## PTZ请求 #1
操作动作: [向左移动/向右移动/向上移动/向下移动/缩放等]
请求URL: https://192.168.31.146/
请求方法: [GET/POST/PUT]
状态码: [200/404/等]

### 请求参数 (URL参数或表单数据):
参数名1 = 参数值1
参数名2 = 参数值2

### 请求头 (重要的几个):
Content-Type:
Authorization:
User-Agent:

### 请求体 (如果是POST请求):
[JSON格式数据或表单数据]

### 响应内容:
[服务器返回的内容]

---

## PTZ请求 #2
操作动作:
请求URL:
请求方法:
状态码:

### 请求参数:


### 请求头:


### 请求体:


### 响应内容:


---

## cURL命令 (如果可以复制)
[右键请求 -> Copy as cURL 的结果]

"""

    return template

def main():
    """主函数"""
    print("🔍 PTZ请求信息提取工具")
    print("=" * 50)

    # 创建指南文件
    guide = create_extraction_guide()
    guide_file = f"PTZ_提取指南_{time.strftime('%Y%m%d_%H%M%S')}.txt"

    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)

    print(f"📖 提取指南已生成: {guide_file}")

    # 创建模板文件
    template = create_request_template()
    template_file = f"PTZ_请求模板_{time.strftime('%Y%m%d_%H%M%S')}.txt"

    with open(template_file, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"📝 填写模板已生成: {template_file}")
    print()

    # 显示快速指南
    print("🎯 快速指南:")
    print("1. 在浏览器开发者工具中操作PTZ控制")
    print("2. 观察Network标签页中的请求")
    print("3. 找到PTZ相关请求后，将信息填入模板")
    print("4. 提供给我分析")
    print()
    print("📋 我特别需要的信息:")
    print("- 完整的请求URL")
    print("- 请求方法和参数")
    print("- 成功请求的响应内容")
    print()
    print("💡 提示: 可以右键请求选择 'Copy as cURL' 获取完整命令")

if __name__ == "__main__":
    import time
    main()