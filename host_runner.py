import subprocess
import time
import sys

def run_services():
    print("[Cookie Bot Host Runner] Starting auto-restart hosting...")
    
    web_server_proc = None
    bot_proc = None

    while True:
        try:
            # Check web_server.py
            if web_server_proc is None or web_server_proc.poll() is not None:
                print("Starting web_server.py...")
                web_server_proc = subprocess.Popen([sys.executable, "web_server.py"])

            # Check main.py
            if bot_proc is None or bot_proc.poll() is not None:
                print("Starting main.py...")
                bot_proc = subprocess.Popen([sys.executable, "main.py"])

            time.sleep(5)
        except KeyboardInterrupt:
            print("Stopping host_runner.")
            if web_server_proc:
                web_server_proc.terminate()
            if bot_proc:
                bot_proc.terminate()
            break
        except Exception as e:
            print(f"Error in host_runner: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run_services()
