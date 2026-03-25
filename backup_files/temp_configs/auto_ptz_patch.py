
# 自动SessionId PTZ控制器替换
class AutoSessionPTZController:
    def __init__(self):
        self.session_id = "AB3370235EB91CD36BCE19EDB47F6FE"
        import os
        os.environ['OPENSSL_CONF'] = '/tmp/openssl_legacy.conf'
        self.last_command_time = 0
        self.command_cooldown = 0.1

    def send_command(self, action):
        import subprocess
        import json
        import time

        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return True

        command_map = {
            'up': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": 120}},
            'down': {"method": "ptz_move_start", "param": {"channelid": 0, "tiltUp": -120}},
            'left': {"method": "ptz_move_start", "param": {"channelid": 0, "panLeft": 120}},
            'right': {"method": "ptz_move_start", "param": {"channelid": 0, "panRight": 120}},
            'stop': {"method": "ptz_move_stop", "param": {"channelid": 0}},
            'zoom_in': {"method": "ptz_move_start", "param": {"channelid": 0, "zoomIn": 120}},
            'zoom_out': {"method": "ptz_move_start", "param": {"channelid": 0, "zoomOut": 120}},
        }

        if action not in command_map:
            return False

        data = command_map[action]
        curl_cmd = [
            "curl", "-s", "--insecure", "--connect-timeout", "3",
            "-H", "Content-Type: application/json",
            "-H", f"SessionId: {self.session_id}",
            "--data-raw", json.dumps(data),
            "https://192.168.31.146/ipc/grpc_cmd"
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=8)
            self.last_command_time = current_time
            success = result.returncode == 0
            print(f"PTZ命令 {action}: {'成功' if success else '失败'}")
            return success
        except:
            return False

# 用自动SessionId控制器替换原有的PTZControllerAdapter
PTZControllerAdapter = AutoSessionPTZController
