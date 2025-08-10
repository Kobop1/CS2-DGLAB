import qrcode
from PIL import Image
from pathlib import Path

def generate_qrcode(data: str, save_path: str = "temp_qrcode.png") -> str:
    """生成二维码并保存图片"""
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
    