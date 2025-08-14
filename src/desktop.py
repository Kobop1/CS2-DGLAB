import webview
import threading
import uvicorn
from src.api.main import app
import multiprocessing
import os
import sys

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境路径
    return os.path.join(os.path.abspath("."), relative_path)

def run_server():
    """在单独线程中运行FastAPI服务器"""
    frontend_dir = get_resource_path(os.path.join('src', 'frontend'))
    if not os.path.exists(frontend_dir):
        os.makedirs(frontend_dir)
        
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        reload=False
    )

def start_desktop_app():
    """启动桌面应用"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 配置窗口
    window_options = {
        "title": "CS2&DGLab",
        "width": 1024,
        "height": 768,
        "resizable": True,
        "min_size": (800, 600),
        "frameless": True,
        "easy_drag": True 
        
    }
    
    # 创建窗口并加载本地页面
    window = webview.create_window(
        **window_options,
        url="http://127.0.0.1:8000/static/index.html"
    )
    
    # 启动WebView事件循环
    webview.start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    start_desktop_app()