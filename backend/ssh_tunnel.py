import os
import time
import socket
import subprocess
import atexit
import sys
import requests

# Global variable to hold the SSH tunnel process reference
_tunnel_process = None

def setup_ssh_key_permissions(ssh_key_path):
    """
    On Windows, OpenSSH client requires strict permissions for the private key.
    This function uses icacls to configure the file permissions so that only 
    the current user can read the file.
    """
    if sys.platform.startswith('win'):
        print(f"[SSH-Tunnel] Configuring Windows file permissions for {ssh_key_path}...")
        try:
            # Normalize path for Windows
            norm_key_path = os.path.abspath(ssh_key_path)
            
            # Disable inheritance
            cmd_disable = f'icacls "{norm_key_path}" /inheritance:r'
            subprocess.run(cmd_disable, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Grant read permissions to current user
            username = os.environ.get("USERNAME") or os.getlogin()
            cmd_grant = f'icacls "{norm_key_path}" /grant:r "{username}":(R)'
            subprocess.run(cmd_grant, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print("[SSH-Tunnel] [OK] SSH key permissions successfully set.")
        except Exception as e:
            print(f"[SSH-Tunnel] [WARN] Warning: Failed to set key permissions: {e}")
    else:
        # On POSIX systems, set standard chmod 600
        try:
            os.chmod(ssh_key_path, 0o600)
            print(f"[SSH-Tunnel] Set permission 600 for {ssh_key_path}")
        except Exception as e:
            print(f"[SSH-Tunnel] [WARN] Warning: Failed to set key permissions: {e}")

def is_socks_proxy_listening(port):
    """
    Test if the local port is open and listening.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(1.0)
            s.connect(('127.0.0.1', port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False

def verify_public_ip(socks_port, expected_ip):
    """
    Make an HTTP request through the SOCKS5 proxy to verify that
    outgoing requests originate from the AWS static IP.
    """
    proxies = {
        "http": f"socks5h://127.0.0.1:{socks_port}",
        "https": f"socks5h://127.0.0.1:{socks_port}"
    }
    
    # We use a short timeout for verification
    try:
        print(f"[SSH-Tunnel] Verifying routing IP via SOCKS5 proxy on port {socks_port}...")
        response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10.0)
        if response.status_code == 200:
            current_ip = response.json().get("ip")
            print(f"[SSH-Tunnel] Outgoing Request IP: {current_ip}")
            if current_ip == expected_ip:
                print(f"[SSH-Tunnel] [SUCCESS] IP matches AWS Static IP ({expected_ip}).")
                return True
            else:
                print(f"[SSH-Tunnel] [FAIL] Mismatch! Got {current_ip}, expected {expected_ip}.")
                return False
        else:
            print(f"[SSH-Tunnel] [FAIL] IP check failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"[SSH-Tunnel] [FAIL] Failed to route request through SOCKS5 proxy: {e}")
        return False

def start_tunnel():
    """
    Start the SSH SOCKS5 tunnel as a background subprocess.
    """
    global _tunnel_process
    
    # Check if proxy is enabled
    use_proxy = os.getenv("USE_AWS_PROXY", "false").lower() == "true"
    if not use_proxy:
        print("[SSH-Tunnel] AWS SOCKS Proxy routing is disabled in settings.")
        return True
        
    static_ip = os.getenv("AWS_STATIC_IP")
    ssh_user = os.getenv("AWS_SSH_USER", "ubuntu")
    ssh_key_path = os.getenv("AWS_SSH_KEY_PATH")
    socks_port = int(os.getenv("AWS_SOCKS_PORT", "1080"))
    
    if not static_ip or not ssh_key_path:
        print("[SSH-Tunnel] [FAIL] Missing AWS SOCKS proxy configuration (AWS_STATIC_IP or AWS_SSH_KEY_PATH).")
        return False

    if not os.path.exists(ssh_key_path):
        print(f"[SSH-Tunnel] [FAIL] Private key not found at: {ssh_key_path}")
        return False

    # 1. Setup proper permissions for key file
    setup_ssh_key_permissions(ssh_key_path)
    
    # 2. Check if port is already in use by a stale tunnel or process
    if is_socks_proxy_listening(socks_port):
        print(f"[SSH-Tunnel] Port {socks_port} is already listening. Checking if routing is active...")
        if verify_public_ip(socks_port, static_ip):
            print(f"[SSH-Tunnel] [OK] Reusing existing healthy tunnel on port {socks_port}.")
            return True
        else:
            print(f"[SSH-Tunnel] [WARN] Port {socks_port} is active but routing is invalid. Will attempt to start a new tunnel.")

    # 3. Start SSH process
    ssh_command = [
        "ssh",
        "-i", os.path.abspath(ssh_key_path),
        "-N",
        "-D", str(socks_port),
        f"{ssh_user}@{static_ip}",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10"
    ]
    
    print(f"[SSH-Tunnel] Launching SSH Tunnel: {' '.join(ssh_command)}")
    
    try:
        # Start SSH process in background
        _tunnel_process = subprocess.Popen(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
        )
        
        # Register cleanup on program exit
        atexit.register(stop_tunnel)
        
        # Wait up to 10 seconds for SOCKS proxy to listen
        print("[SSH-Tunnel] Waiting for SOCKS5 proxy to initialize...")
        for _ in range(20):
            if is_socks_proxy_listening(socks_port):
                break
            time.sleep(0.5)
            # Check if subprocess terminated early
            if _tunnel_process.poll() is not None:
                _, stderr = _tunnel_process.communicate()
                print(f"[SSH-Tunnel] [FAIL] SSH client exited early with error: {stderr.decode('utf-8', errors='ignore')}")
                return False
        
        if not is_socks_proxy_listening(socks_port):
            print(f"[SSH-Tunnel] [FAIL] Timeout waiting for SOCKS5 proxy to listen on port {socks_port}.")
            stop_tunnel()
            return False
            
        # 4. Verify routing IP
        if verify_public_ip(socks_port, static_ip):
            print("[SSH-Tunnel] [OK] SSH SOCKS5 Tunnel successfully established and verified!")
            return True
        else:
            print("[SSH-Tunnel] [FAIL] SOCKS5 proxy started but routing test failed.")
            stop_tunnel()
            return False
            
    except Exception as e:
        print(f"[SSH-Tunnel] [FAIL] Failed to launch SSH tunnel process: {e}")
        return False

def stop_tunnel():
    """
    Terminate the SSH tunnel process.
    """
    global _tunnel_process
    if _tunnel_process:
        print("[SSH-Tunnel] Stopping SSH Tunnel process...")
        try:
            _tunnel_process.terminate()
            _tunnel_process.wait(timeout=2.0)
            print("[SSH-Tunnel] SSH Tunnel process stopped.")
        except subprocess.TimeoutExpired:
            _tunnel_process.kill()
            print("[SSH-Tunnel] SSH Tunnel process force-killed.")
        except Exception as e:
            print(f"[SSH-Tunnel] Exception while stopping tunnel: {e}")
        _tunnel_process = None
