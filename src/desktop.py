import webview
import threading
import uvicorn
from src.api.main import app
import multiprocessing
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio

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

def run_obs_server():
    """运行OBS页面服务器"""
    obs_app = FastAPI(title="CS2&DGLab OBS Server")
    frontend_dir = get_resource_path(os.path.join('src', 'frontend'))
    
    # 只提供obs.html页面
    @obs_app.get("/", response_class=HTMLResponse)
    async def get_obs_page():
        obs_html_path = os.path.join(frontend_dir, "obs.html")
        if os.path.exists(obs_html_path):
            with open(obs_html_path, "r", encoding="utf-8") as f:
                return f.read()
        return "<h1>OBS Page Not Found</h1>"
    
    # 挂载静态文件目录，以便CSS和JS等资源可以被访问
    if os.path.exists(frontend_dir):
        obs_app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    
    uvicorn.run(
        obs_app,
        host="127.0.0.1",
        port=8001,
        log_level="warning",
        reload=False
    )

def start_desktop_app():
    """启动桌面应用"""
    # 启动主服务器
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 启动OBS服务器
    obs_server_thread = threading.Thread(target=run_obs_server, daemon=True)
    obs_server_thread.start()
    
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