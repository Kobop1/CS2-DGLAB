import qrcode
from PIL import Image
from pathlib import Path
import os
import sys

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境路径
    return os.path.join(os.path.abspath("."), relative_path)

def generate_qrcode(data: str, save_path: str = None) -> str:
    """生成二维码并保存图片"""
    # 如果没有指定保存路径，使用默认路径
    if save_path is None:
        frontend_dir = get_resource_path("src/frontend")
        if not os.path.exists(frontend_dir):
            os.makedirs(frontend_dir)
        save_path = os.path.join(frontend_dir, "temp_qrcode.png")
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = Path(save_path)
    img.save(img_path)
    return str(img_path)