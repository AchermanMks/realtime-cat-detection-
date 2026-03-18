#!/bin/bash
# PTZ快速测试 - 常见命令

echo '快速测试 1:'
echo 'curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"'
curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"
echo ''
echo '快速测试 2:'
echo 'curl -k -u admin:admin123 "https://192.168.31.146/api/ptz?cmd=left&speed=3"'
curl -k -u admin:admin123 "https://192.168.31.146/api/ptz?cmd=left&speed=3"
echo ''
echo '快速测试 3:'
echo 'curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action":"move","direction":"left","speed":5}' "https://192.168.31.146/api/ptz"'
curl -k -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"action":"move","direction":"left","speed":5}' "https://192.168.31.146/api/ptz"
echo ''
echo '快速测试 4:'
echo 'curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=5"'
curl -k -u admin:admin123 "https://192.168.31.146/cgi-bin/hi3510/ptzctrl.cgi?-step=0&-act=left&-speed=5"
echo ''
