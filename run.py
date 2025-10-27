# run.py
import socket
import uvicorn
from app.main import app

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("\nFastAPI Location Service Starting!")
    print(f"Access locally: http://127.0.0.1:8000/")
    print(f"Access on LAN:  http://{local_ip}:8000/\n")

    # Run using import string for reload/workers support
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=1, reload=True)
