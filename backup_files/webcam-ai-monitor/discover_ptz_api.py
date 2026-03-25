#!/usr/bin/env python3
"""
PTZ API发现工具 - 寻找真实的PTZ控制端点
"""

import requests
import json
from urllib.parse import quote
import xml.etree.ElementTree as ET

def test_ptz_apis():
    """测试各种PTZ API格式"""

    camera_ip = "192.168.31.146"
    username = "admin"
    password = "admin"

    print("🔍 PTZ API发现工具")
    print("=" * 50)

    # JOVISION可能的PTZ API格式
    ptz_apis = [
        # HTTP方式
        {"method": "GET", "url": "http://{ip}/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=5&arg2=5", "desc": "大华格式1"},
        {"method": "GET", "url": "http://{ip}/cgi-bin/ptz.cgi?move=left&speed=50", "desc": "通用格式1"},
        {"method": "GET", "url": "http://{ip}/web/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=50", "desc": "海思芯片格式"},
        {"method": "GET", "url": "http://{ip}/axis-cgi/com/ptz.cgi?move=left", "desc": "Axis格式"},
        {"method": "GET", "url": "http://{ip}/decoder_control.cgi?loginuse={user}&loginpas={password}&command=0&onestep=1", "desc": "解码器格式"},

        # JOVISION特有格式
        {"method": "GET", "url": "http://{ip}/cgi-bin/hi3510/param.cgi?cmd=setserialattr&-data=0,Left,50", "desc": "JOVISION串口格式"},
        {"method": "GET", "url": "http://{ip}/cgi-bin/configManager.cgi?action=setConfig&PTZProtocol.Enable=true&PTZProtocol.Address=1", "desc": "JOVISION配置格式"},

        # POST方式JSON
        {"method": "POST", "url": "http://{ip}/api/ptz", "data": {"cmd": "move", "direction": "left", "speed": 50}, "desc": "JSON API格式"},
        {"method": "POST", "url": "http://{ip}/cgi-bin/ptz", "data": "action=move&direction=left&speed=50", "desc": "POST表单格式"},

        # 可能的RTSP命令
        {"method": "GET", "url": "http://{ip}/cgi-bin/rtsp.cgi?cmd=ptz&direction=left&speed=50", "desc": "RTSP控制格式"},
    ]

    # HTTPS版本
    https_apis = []
    for api in ptz_apis:
        https_api = api.copy()
        https_api["url"] = https_api["url"].replace("http://", "https://")
        https_api["desc"] += " (HTTPS)"
        https_apis.append(https_api)

    all_apis = ptz_apis + https_apis

    working_apis = []

    for i, api in enumerate(all_apis):
        print(f"\n🔍 测试 {i+1}/{len(all_apis)}: {api['desc']}")

        try:
            url = api["url"].format(ip=camera_ip, user=username, password=password)
            print(f"   URL: {url}")

            if api["method"] == "GET":
                response = requests.get(url, auth=(username, password), timeout=3, verify=False)
            else:  # POST
                if isinstance(api.get("data"), dict):
                    response = requests.post(url, json=api["data"], auth=(username, password), timeout=3, verify=False)
                else:
                    response = requests.post(url, data=api["data"], auth=(username, password), timeout=3, verify=False)

            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.text[:100]}...")

            if response.status_code == 200:
                # 检查响应内容是否表示成功
                response_lower = response.text.lower()
                if any(keyword in response_lower for keyword in ['ok', 'success', 'true', '"result":0']):
                    print("   ✅ 可能的工作端点!")
                    working_apis.append({
                        "api": api,
                        "url": url,
                        "response": response.text[:200]
                    })
                elif response.status_code == 200 and len(response.text) < 10:
                    print("   ✅ 简短响应，可能成功!")
                    working_apis.append({
                        "api": api,
                        "url": url,
                        "response": response.text
                    })
                else:
                    print("   ⚠️ 200状态但响应内容不确定")
            elif response.status_code == 401:
                print("   ❌ 认证失败")
            elif response.status_code == 404:
                print("   ❌ 端点不存在")
            else:
                print(f"   ❌ 失败: HTTP {response.status_code}")

        except requests.exceptions.SSLError:
            print("   ❌ SSL证书错误")
        except requests.exceptions.ConnectTimeout:
            print("   ❌ 连接超时")
        except Exception as e:
            print(f"   ❌ 异常: {str(e)[:50]}...")

    print("\n" + "=" * 50)
    print("🎯 发现结果:")

    if working_apis:
        print(f"✅ 找到 {len(working_apis)} 个可能的工作端点:")
        for i, result in enumerate(working_apis):
            print(f"\n{i+1}. {result['api']['desc']}")
            print(f"   URL: {result['url']}")
            print(f"   响应: {result['response']}")
    else:
        print("❌ 没有找到工作的PTZ端点")
        print("\n💡 建议:")
        print("1. 检查摄像头Web管理界面")
        print("2. 确认PTZ功能已启用")
        print("3. 尝试其他用户名/密码")
        print("4. 查看摄像头说明书中的API文档")

if __name__ == "__main__":
    test_ptz_apis()