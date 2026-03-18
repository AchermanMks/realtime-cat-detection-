#!/usr/bin/env python3

import subprocess
import os

def test_ptz():
    """Simple PTZ test using exact same format as working shell script"""

    # Clear proxy environment variables
    env = os.environ.copy()
    env.pop('https_proxy', None)
    env.pop('http_proxy', None)

    # Exact same command as in simple_control.sh
    cmd = [
        "curl", "--insecure", "-s",
        "https://192.168.31.146/ipc/grpc_cmd",
        "-H", "Content-Type: application/json",
        "-H", "SessionId: D1D66678A96617EF9555E42E67349E2",
        "--data-raw", '{"method":"ptz_move_stop","param":{"channelid":0}}'
    ]

    print("Testing PTZ connection with stop command...")
    print(f"Command: {' '.join(cmd)}")

    try:
        # Try with shell=True like the shell script
        shell_cmd = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd])
        shell_cmd = f"unset https_proxy http_proxy && {shell_cmd}"

        print(f"Shell command: {shell_cmd}")

        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_ptz()