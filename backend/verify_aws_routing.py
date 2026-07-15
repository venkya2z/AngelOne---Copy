import os
import requests
from dotenv import load_dotenv
import ssh_tunnel

def main():
    print("=" * 60)
    print("AWS STATIC IP ROUTING VERIFICATION")
    print("=" * 60)
    
    # Load env vars
    load_dotenv()
    
    expected_ip = os.getenv("AWS_STATIC_IP")
    socks_port = os.getenv("AWS_SOCKS_PORT", "1080")
    
    print(f"Configured Expected Static IP: {expected_ip}")
    print(f"Configured SOCKS5 Proxy Port: {socks_port}")
    
    # 1. Test direct connection
    try:
        print("\n[Step 1] Checking current direct public IP (before proxy)...")
        res = requests.get("https://api.ipify.org?format=json", timeout=10.0)
        direct_ip = res.json().get("ip")
        print(f"Direct connection public IP: {direct_ip}")
    except Exception as e:
        print(f"Warning: Direct IP check failed: {e}")
        direct_ip = None

    # 2. Start SSH tunnel
    print("\n[Step 2] Attempting to establish AWS SSH tunnel...")
    success = ssh_tunnel.start_tunnel()
    
    if success:
        print("\n[Step 3] Verifying connection through SOCKS5 proxy...")
        proxies = {
            "http": f"socks5h://127.0.0.1:{socks_port}",
            "https": f"socks5h://127.0.0.1:{socks_port}"
        }
        try:
            res_proxied = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10.0)
            proxied_ip = res_proxied.json().get("ip")
            print(f"Proxied connection public IP: {proxied_ip}")
            
            if proxied_ip == expected_ip:
                print("\n[SUCCESS] VERIFICATION SUCCESSFUL!")
                print(f"Direct IP: {direct_ip}")
                print(f"Proxied IP: {proxied_ip} (Matches AWS Static IP)")
            else:
                print("\n[FAILURE] VERIFICATION FAILED: Proxied IP does not match expected AWS Static IP.")
        except Exception as e:
            print(f"\n[FAILURE] VERIFICATION FAILED: Error routing through SOCKS5 proxy: {e}")
    else:
        print("\n[FAILURE] VERIFICATION FAILED: Failed to start SSH tunnel.")
        
    print("\nCleaning up and closing tunnel...")
    ssh_tunnel.stop_tunnel()
    print("Done.")
    print("=" * 60)

if __name__ == "__main__":
    main()
