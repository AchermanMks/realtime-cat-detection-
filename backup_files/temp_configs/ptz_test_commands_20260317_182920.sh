#!/bin/bash
# PTZ测试命令

echo '测试: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Left&arg1=0&arg2=5"
sleep 1

echo '测试: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Right&arg1=0&arg2=5"
sleep 1

echo '测试: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Up&arg1=0&arg2=5"
sleep 1

echo '测试: curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5"'
curl  -u admin:admin123 "http://192.168.31.146/cgi-bin/ptz.cgi?action=start&channel=0&code=Down&arg1=0&arg2=5"
sleep 1

echo '测试: curl  -u admin:admin123 "http://192.168.31.146/api/ptz?cmd=left&speed=3"'
curl  -u admin:admin123 "http://192.168.31.146/api/ptz?cmd=left&speed=3"
sleep 1

echo '测试: curl  -u admin:admin123 -X POST -d "action=moveLeft&speed=3" "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -d "action=moveLeft&speed=3" "http://192.168.31.146/api/ptz"
sleep 1

echo '测试: curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command":"moveLeft","speed":3}' "http://192.168.31.146/api/ptz"'
curl  -u admin:admin123 -X POST -H "Content-Type: application/json" -d '{"command":"moveLeft","speed":3}' "http://192.168.31.146/api/ptz"
sleep 1

