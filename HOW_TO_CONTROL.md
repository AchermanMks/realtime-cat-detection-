# 🎮 如何控制摄像头PTZ - 完整指南

## 🚀 **立即开始 (3种方法):**

### **方法1: 运行自动测试** (推荐新手)
```bash
./perfect_ptz_test.sh
```
自动演示所有控制功能，摄像头会自动移动！

### **方法2: 手动单命令控制** (推荐高级用户)

#### 基本移动命令：

**向左移动：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
```

**向右移动：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":-120}}'
```

**向上移动：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":120}}'
```

**向下移动：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"tiltUp":-120}}'
```

**停止移动 (重要!)：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
```

### **方法3: Python交互式控制**
```bash
python3 realtime_ptz_controller.py
```
然后选择：
- 选项1: 键盘实时控制 (W/A/S/D键控制)
- 选项4: 快速测试

## 🎯 **控制技巧：**

### **速度控制：**
- 慢速: 50-80
- 中速: 120 (默认)
- 快速: 200-255

### **对角线移动：**
```bash
# 左上移动
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120,"tiltUp":120}}'
```

### **缩放控制：**

**放大：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomIn":120}}'
```

**缩小：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_zoom_start","param":{"channelid":0,"zoomOut":120}}'
```

**停止缩放：**
```bash
curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
  -H 'Content-Type: application/json' \
  -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
  --data-raw '{"method":"ptz_zoom_stop","param":{"channelid":0}}'
```

## 📱 **简化版快速命令：**

为了方便使用，可以设置环境变量：

```bash
# 设置快捷变量
export PTZ_URL="https://192.168.31.146/ipc/grpc_cmd"
export PTZ_SESSION="D1D66678A96617EF9555E42E67349E2"

# 快速控制函数
ptz_left() {
    curl --insecure "$PTZ_URL" \
        -H 'Content-Type: application/json' \
        -H "SessionId: $PTZ_SESSION" \
        --data-raw '{"method":"ptz_move_start","param":{"channelid":0,"panLeft":120}}'
}

ptz_stop() {
    curl --insecure "$PTZ_URL" \
        -H 'Content-Type: application/json' \
        -H "SessionId: $PTZ_SESSION" \
        --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
}

# 使用方法
ptz_left    # 向左移动
ptz_stop    # 停止移动
```

## 🌐 **Web界面控制：**

生成Web控制页面：
```bash
python3 realtime_ptz_controller.py
# 选择选项3生成Web界面
```

然后在浏览器打开 `ptz_web_control.html`

## ⚠️ **重要注意事项：**

1. **必须手动停止**：摄像头移动后不会自动停止，必须发送停止命令
2. **SessionId有效期**：如果控制失败，可能需要更新SessionId
3. **速度范围**：建议速度值在50-255之间
4. **网络延迟**：命令执行可能有1-2秒延迟

## 🔧 **故障排除：**

**如果控制不响应：**

1. **检查SessionId**：
   ```bash
   # 在浏览器开发者工具中获取新的SessionId
   ```

2. **测试连接**：
   ```bash
   curl --insecure 'https://192.168.31.146/ipc/grpc_cmd' \
       -H 'Content-Type: application/json' \
       -H 'SessionId: D1D66678A96617EF9555E42E67349E2' \
       --data-raw '{"method":"ptz_move_stop","param":{"channelid":0}}'
   ```

3. **强制停止**：
   ```bash
   # 如果摄像头卡在移动状态，发送停止命令
   ./perfect_ptz_test.sh  # 脚本末尾会发送停止命令
   ```

## 📋 **快速参考卡：**

| 动作 | panLeft值 | tiltUp值 | 说明 |
|------|-----------|----------|------|
| 向左 | 120 | - | 正值向左 |
| 向右 | -120 | - | 负值向右 |
| 向上 | - | 120 | 正值向上 |
| 向下 | - | -120 | 负值向下 |
| 左上 | 120 | 120 | 组合移动 |
| 右下 | -120 | -120 | 组合移动 |
| 停止 | - | - | ptz_move_stop |

## 🎉 **开始控制吧！**

最简单的开始方式：
```bash
./perfect_ptz_test.sh
```

这会让摄像头自动演示所有动作，您可以在监控画面中看到效果！