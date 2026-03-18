# 小米摄像头PTZ控制器

基于从Web界面抓取的curl命令，实现对小米摄像头PTZ功能的完整控制。

## 📁 文件说明

### 1. xiaomi_ptz_controller.py
原始的PTZ控制器，已更新为符合真实API协议。

**功能特点:**
- 支持登录认证
- 方向控制 (上/下/左/右)
- 缩放控制 (放大/缩小)
- 预设位管理
- 交互式控制界面

**使用方法:**
```bash
# 交互式控制模式
python xiaomi_ptz_controller.py

# 测试模式
python xiaomi_ptz_controller.py test

# 指定交互模式
python xiaomi_ptz_controller.py interactive
```

### 2. web_ptz_controller.py
基于Flask的Web界面PTZ控制器。

**功能特点:**
- 现代化Web界面
- 支持鼠标和键盘控制
- 实时日志显示
- 移动设备友好
- 预设位快速访问

**使用方法:**
```bash
# 启动Web服务器
python web_ptz_controller.py

# 打开浏览器访问
http://localhost:5000
```

**依赖安装:**
```bash
pip install flask requests urllib3
```

**Web界面控制:**
- 鼠标: 按住方向按钮控制移动
- 键盘: W/A/S/D控制方向，Q/E控制缩放，空格停止
- 触摸: 支持移动设备触摸控制

### 3. curl_ptz_controller.py
直接基于curl命令的PTZ控制器，完全复制Web界面的API调用。

**功能特点:**
- 直接使用系统curl命令
- 完全模拟浏览器行为
- 显示等效curl命令示例
- 适合调试和学习API

**使用方法:**
```bash
# 交互式控制
python curl_ptz_controller.py

# 测试模式
python curl_ptz_controller.py test

# 显示curl命令示例
python curl_ptz_controller.py curl
```

## 🔧 API协议说明

基于抓取的curl命令，小米摄像头使用以下API协议:

### 登录接口
```bash
POST https://192.168.31.146/ipc/login
Content-Type: application/json

{"username":"admin","password":"admin123"}
```

**响应格式:**
```json
{
  "result": 0,
  "param": {
    "sessionid": "921B4E790DBB846BF5F300428A4BF66"
  }
}
```

### PTZ控制接口
```bash
POST https://192.168.31.146/ipc/grpc_cmd
Content-Type: application/json
SessionId: 921B4E790DBB846BF5F300428A4BF66

{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}
```

### 支持的PTZ命令

| 命令 | 方法 | 参数 | 说明 |
|------|------|------|------|
| 向上移动 | ptz_move_start | {"tiltUp": 120} | 正值向上 |
| 向下移动 | ptz_move_start | {"tiltUp": -120} | 负值向下 |
| 向左移动 | ptz_move_start | {"panLeft": 120} | 左移 |
| 向右移动 | ptz_move_start | {"panRight": 120} | 右移 |
| 放大 | ptz_move_start | {"zoomIn": 120} | 缩放 |
| 缩小 | ptz_move_start | {"zoomOut": 120} | 缩放 |
| 停止移动 | ptz_move_stop | {} | 停止所有动作 |
| 转到预设位 | ptz_preset_goto | {"presetId": 1} | 预设位1-8 |
| 保存预设位 | ptz_preset_set | {"presetId": 1} | 保存当前位置 |

## 🎮 控制说明

### 交互式控制键位
- **W**: 向上移动
- **S**: 向下移动
- **A**: 向左移动
- **D**: 向右移动
- **Q**: 放大
- **E**: 缩小
- **空格**: 停止移动
- **1-8**: 转到预设位
- **P**: 获取PTZ信息
- **H**: 显示帮助
- **Quit**: 退出

### 速度参数
- **60**: 慢速
- **120**: 中速 (默认)
- **180**: 快速

## 🔗 网络配置

### 默认配置
- **IP地址**: 192.168.31.146
- **用户名**: admin
- **密码**: admin123
- **端口**: HTTPS 443

### 修改配置
可以在运行时输入不同的IP地址和认证信息，或直接修改脚本中的默认值。

## 🛡️ 安全说明

- 所有脚本都禁用了SSL证书验证 (`--insecure`)
- SessionId具有时效性，失效后会自动重新登录
- 建议在可信网络环境中使用

## 🧪 测试和调试

### 测试连接
```bash
# 测试基本功能
python curl_ptz_controller.py test

# 显示原始curl命令
python curl_ptz_controller.py curl
```

### 调试信息
所有脚本都包含详细的日志输出，可以查看:
- 登录状态
- 命令发送情况
- 响应结果
- 错误信息

### 常见问题

1. **连接失败**: 检查IP地址和网络连接
2. **认证失败**: 检查用户名和密码
3. **命令无响应**: 检查SessionId是否有效
4. **移动不停止**: 手动发送停止命令

## 📋 curl命令示例

完整的curl命令示例 (可直接在终端使用):

```bash
# 1. 登录获取SessionId
SESSION_ID=$(curl -s 'https://192.168.31.146/ipc/login' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  --data-raw '{"username":"admin","password":"admin123"}' \
  --insecure | jq -r '.param.sessionid')

# 2. 向上移动
curl -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}' \
  --insecure

# 3. 停止移动
curl -s 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json; charset=UTF-8' \
  -H "SessionId: $SESSION_ID" \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}' \
  --insecure
```

## 🚀 快速开始

1. **选择控制方式:**
   - Web界面: `python web_ptz_controller.py`
   - 命令行: `python xiaomi_ptz_controller.py`
   - 纯curl: `python curl_ptz_controller.py`

2. **输入摄像头信息** (或使用默认值)

3. **开始控制PTZ功能**

享受你的PTZ控制体验！ 🎥✨