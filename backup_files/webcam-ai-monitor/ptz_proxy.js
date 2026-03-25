#!/usr/bin/env node

const https = require('https');
const http = require('http');

// 禁用SSL证书验证
process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0';

// 设置更宽松的SSL选项
const agent = new https.Agent({
    rejectUnauthorized: false,
    secureProtocol: 'SSLv23_method',
    secureOptions: require('constants').SSL_OP_LEGACY_SERVER_CONNECT
});

function sendPTZCommand(method, params) {
    const payload = {
        method: method,
        param: {
            channelid: 0,
            ...params
        }
    };

    const postData = JSON.stringify(payload);

    const options = {
        hostname: '192.168.31.146',
        port: 443,
        path: '/ipc/grpc_cmd',
        method: 'POST',
        agent: agent,
        headers: {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/json; charset=UTF-8',
            'Content-Length': postData.length,
            'SessionId': '8E7EB2F6FE2304F134901333A05631A',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Origin': 'https://192.168.31.146'
        }
    };

    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            res.on('end', () => {
                console.log(`✅ ${method} 成功: ${data}`);
                resolve(data);
            });
        });

        req.on('error', (error) => {
            console.log(`❌ ${method} 失败:`, error.message);
            reject(error);
        });

        req.write(postData);
        req.end();
    });
}

// 测试PTZ控制
async function testPTZ() {
    console.log('🎯 开始PTZ测试...');

    try {
        await sendPTZCommand('ptz_move_start', {panLeft: 120});
        await new Promise(resolve => setTimeout(resolve, 2000));

        await sendPTZCommand('ptz_move_stop', {});
        await new Promise(resolve => setTimeout(resolve, 1000));

        await sendPTZCommand('ptz_move_start', {panLeft: -120});
        await new Promise(resolve => setTimeout(resolve, 2000));

        await sendPTZCommand('ptz_move_stop', {});

        console.log('🎉 PTZ测试完成!');
    } catch (error) {
        console.log('❌ 测试失败:', error.message);
    }
}

// 创建HTTP代理服务器
const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.url.startsWith('/ptz/')) {
        const action = req.url.split('/')[2];

        try {
            let result;
            switch(action) {
                case 'left':
                    result = await sendPTZCommand('ptz_move_start', {panLeft: 120});
                    break;
                case 'right':
                    result = await sendPTZCommand('ptz_move_start', {panLeft: -120});
                    break;
                case 'up':
                    result = await sendPTZCommand('ptz_move_start', {tiltUp: 120});
                    break;
                case 'down':
                    result = await sendPTZCommand('ptz_move_start', {tiltUp: -120});
                    break;
                case 'stop':
                    result = await sendPTZCommand('ptz_move_stop', {});
                    break;
                case 'zoom_in':
                    result = await sendPTZCommand('ptz_zoom_start', {zoomIn: 120});
                    break;
                case 'zoom_out':
                    result = await sendPTZCommand('ptz_zoom_start', {zoomOut: 120});
                    break;
                default:
                    res.writeHead(404);
                    res.end('Unknown action');
                    return;
            }

            res.writeHead(200, {'Content-Type': 'text/plain'});
            res.end('success');
        } catch (error) {
            res.writeHead(500);
            res.end('failed');
        }
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

if (process.argv[2] === 'test') {
    // 运行测试
    testPTZ();
} else {
    // 启动代理服务器
    const PORT = 8899;
    server.listen(PORT, () => {
        console.log(`🚀 PTZ代理服务器运行在 http://localhost:${PORT}`);
        console.log('📡 现在可以通过 /ptz/left, /ptz/right 等控制摄像头');
    });
}