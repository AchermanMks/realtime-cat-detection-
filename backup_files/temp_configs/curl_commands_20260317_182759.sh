#!/bin/bash
# PTZ控制测试命令
# 摄像头IP: 192.168.31.146
# 用户名: admin

echo '测试: curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0"'
curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5&arg3=0"
echo ''

echo '测试: curl -k -u admin:admin123 -X POST -d "action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0" "https://192.168.31.146/cgi-bin/ptz.cgi"'
curl -k -u admin:admin123 -X POST -d "action=start&channel=0&code=Right&arg1=0&arg2=5&arg3=0" "https://192.168.31.146/cgi-bin/ptz.cgi"
echo ''

echo '测试: curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command":"ptz","action":"moveUp","speed":"3"}' "https://192.168.31.146/api/ptz"'
curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command":"ptz","action":"moveUp","speed":"3"}' "https://192.168.31.146/api/ptz"
echo ''

echo '测试: curl -k -u admin:admin123 "https://192.168.31.146/PSIA/PTZ/channels/1/continuous?pan=50&tilt=50"'
curl -k -u admin:admin123 "https://192.168.31.146/PSIA/PTZ/channels/1/continuous?pan=50&tilt=50"
echo ''

