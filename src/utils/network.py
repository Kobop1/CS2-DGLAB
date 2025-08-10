import socket

def get_local_ip() -> str:
    """获取本机IP地址（WebSocket格式）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        return f"ws://{ip}:5678"
    except Exception as e:
        raise RuntimeError(f"获取IP地址失败: {e}")
