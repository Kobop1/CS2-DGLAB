import socket
import psutil

def get_local_ip() -> str:
    """获取本机IP地址（WebSocket格式）"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        return f"ws://{ip}:5678"
    except Exception as e:
        raise RuntimeError(f"获取IP地址失败: {e}")

def get_network_interfaces() -> list:
    """获取所有网络接口地址"""
    interfaces = []
    addresses = psutil.net_if_addrs()
    
    for interface_name, interface_addresses in addresses.items():
        for address in interface_addresses:
            if address.family == socket.AF_INET :
                interfaces.append({
                    "name": interface_name,
                    "address": address.address
                })
    
    return interfaces

def get_local_ip_by_interface(interface_name: str) -> str:
    """根据指定网络接口获取IP地址"""
    addresses = psutil.net_if_addrs()
    
    if interface_name in addresses:
        for address in addresses[interface_name]:
            if address.family == socket.AF_INET :
                return f"ws://{address.address}:5678"
    
    # 如果找不到指定接口，回退到默认方法
    return get_local_ip()