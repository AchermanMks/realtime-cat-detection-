#!/bin/bash
# PTZ协议全面测试脚本
# 自动生成于: 2026-03-17 18:31:46

echo '🔧 PTZ协议测试开始...'
echo '按Ctrl+C随时停止测试'
echo ''

echo '📋 测试类型: 海康威视风格'
echo '==================================================='
echo '测试 1: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 2: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 3: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 4: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 5: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=stop&channel=0&code=Left&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=stop&channel=0&code=Left&arg1=0&arg2=5&arg3=0"
sleep 1
echo ''
echo '📋 测试类型: 大华风格'
echo '==================================================='
echo '测试 1: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=LeftUp&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=LeftUp&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 2: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=RightUp&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=RightUp&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 3: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=LeftDown&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=LeftDown&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 4: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=RightDown&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=RightDown&arg1=0&arg2=5&arg3=0"
sleep 1
echo '测试 5: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/camctrl.cgi?action=start&channel=0&code=LeftUp&arg1=0&arg2=5&arg3=0"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/camctrl.cgi?action=start&channel=0&code=LeftUp&arg1=0&arg2=5&arg3=0"
sleep 1
echo ''
echo '📋 测试类型: 现代API风格'
echo '==================================================='
echo '测试 1: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=left&speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=left&speed=5"
sleep 1
echo '测试 2: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=right&speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=right&speed=5"
sleep 1
echo '测试 3: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=up&speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=up&speed=5"
sleep 1
echo '测试 4: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=down&speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?action=move&direction=down&speed=5"
sleep 1
echo '测试 5: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?cmd=left&speed=3"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?cmd=left&speed=3"
sleep 1
echo ''
echo '📋 测试类型: JSON POST'
echo '==================================================='
echo '测试 1: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "left", "speed": 5}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "left", "speed": 5}' "http://192.168.31.146/api/ptz"
sleep 1
echo '测试 2: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "right", "speed": 5}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "right", "speed": 5}' "http://192.168.31.146/api/ptz"
sleep 1
echo '测试 3: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "up", "speed": 5}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "up", "speed": 5}' "http://192.168.31.146/api/ptz"
sleep 1
echo '测试 4: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "down", "speed": 5}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action": "move", "direction": "down", "speed": 5}' "http://192.168.31.146/api/ptz"
sleep 1
echo '测试 5: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command": "ptz", "move": "left", "speed": 3}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command": "ptz", "move": "left", "speed": 3}' "http://192.168.31.146/api/ptz"
sleep 1
echo ''
echo '📋 测试类型: 小米/其他风格'
echo '==================================================='
echo '测试 1: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=preset&-act=goto&-number=1"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=preset&-act=goto&-number=1"
sleep 1
echo '测试 2: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=left&-speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=left&-speed=5"
sleep 1
echo '测试 3: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=right&-speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=right&-speed=5"
sleep 1
echo '测试 4: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=up&-speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=up&-speed=5"
sleep 1
echo '测试 5: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=down&-speed=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/action.cgi?cmd=ptzctrl&-step=0&-act=down&-speed=5"
sleep 1
echo ''
echo '✅ 测试完成'
