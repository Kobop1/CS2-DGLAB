import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from src.core.dglab_controller import DGLabController
from src.core.game_listener import GameStateListener
from src.config.config_manager import ConfigManager
from src.utils.network import get_local_ip
from src.utils.qrcode import generate_qrcode
from src.utils.cs2_path import find_cs2_install_path, setup_cs2_gamestate_cfg
import json
from pydantic import BaseModel
from typing import Any
import webview

app = FastAPI(title="CS2&DGLab 控制中心")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置管理
config = ConfigManager()

# 全局状态
class AppState:
    def __init__(self):
        self.dglab = None
        self.game_listener = None
        self.websocket_connections = []
        self.strength_a = 0
        self.strength_b = 0
        self.qrcode_path = ""
        self.health = 100
        self.player_status = "正常"
        self.round_status = "准备中"

state = AppState()

# 窗口控制API类
class WindowApi:
    def minimize_window(self):
        """最小化窗口"""
        if webview.windows:
            webview.windows[0].minimize()
        return {"status": "success"}
    
    def close_window(self):
        """关闭窗口"""
        if webview.windows:
            webview.windows[0].destroy()
        return {"status": "success"}

# 挂载静态文件
app.mount("/static", StaticFiles(directory="src/frontend"), name="static")

# 数据模型
class ConfigUpdate(BaseModel):
    key: str
    value: Any

# WebSocket管理
async def broadcast(data: dict):
    """向所有连接的客户端广播数据"""
    for connection in state.websocket_connections:
        await connection.send_text(json.dumps(data))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.websocket_connections.append(websocket)
    try:
        while True:
            # 保持连接
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.websocket_connections.remove(websocket)

# API端点
@app.get("/api/status")
async def get_status():
    """获取当前状态"""
    return {
        "strength_a": state.strength_a,
        "strength_b": state.strength_b,
        "health": state.health,
        "player_status": state.player_status,
        "round_status": state.round_status,
        "qrcode_available": state.qrcode_path != "",
        "connected": state.dglab and state.dglab.is_connected
    }

@app.get("/api/qrcode")
async def get_qrcode():
    """获取二维码图片"""
    return {"qrcode_path": "/static/temp_qrcode.png"}

@app.get("/api/config")
async def get_config():
    """获取配置"""
    return config.config

@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """更新配置"""
    config.update(update.key, update.value)
    print(f"更新配置: {update.key} = {update.value}")
    return {"status": "success", "config": config.config}

# 新增窗口控制API端点
@app.post("/api/window/minimize")
async def minimize_window():
    """最小化窗口API"""
    if webview.windows:
        webview.windows[0].minimize()
        return {"status": "success"}
    return {"status": "error", "message": "No window found"}

@app.post("/api/window/close")
async def close_window():
    """关闭窗口API"""
    if webview.windows:
        webview.windows[0].destroy()
        return {"status": "success"}
    return {"status": "error", "message": "No window found"}

# 启动后台任务
# 启动后台任务
async def start_background_tasks():
    """启动所有后台任务"""
    # 初始化DGLab控制器
    ip_address = get_local_ip()
    state.dglab = DGLabController(ip_address)
    
    # 启动DGLab服务
    asyncio.create_task(state.dglab.start())
    # 等待客户端连接建立
    retry_count = 0
    while retry_count < 30 and not state.dglab.client:  # 等待最多3秒
        await asyncio.sleep(0.1)
        retry_count += 1
    
    # 生成二维码
    if state.dglab.client:
        qrcode_url = state.dglab.client.get_qrcode(ip_address)
    else:
        qrcode_url = ip_address
    
    state.qrcode_path = generate_qrcode(qrcode_url, "src/frontend/temp_qrcode.png")
    
    # 查找CS2路径并配置
    try:
        cs2_path = find_cs2_install_path()
        print(f"找到CS2安装路径: {cs2_path}")
        if setup_cs2_gamestate_cfg(cs2_path):
            print("CS2游戏状态配置成功")
        else:
            print("CS2游戏状态配置失败")
    except Exception as e:
        print(f"CS2路径处理警告: {e}")
    
    # 启动游戏状态监听器
    state.game_listener = GameStateListener(config, state.dglab.queue)
    await state.game_listener.start()
    # 启动强度监控任务
    async def monitor_strength():
        while True:
            if state.dglab:
                # 更新强度数据
                state.strength_a = state.dglab.current_strength_A
                state.strength_b = state.dglab.current_strength_B
                
                # 更新游戏状态
                if state.game_listener:
                    state.health = state.game_listener.health
                    state.player_status = state.game_listener.player_status
                    state.round_status = state.game_listener.round_status
                
                # 广播更新
                await broadcast({
                    "type": "status_update",
                    "strength": {
                        "a": state.strength_a,
                        "b": state.strength_b
                    },
                    "game": {
                        "health": state.health,
                        "player_status": state.player_status,
                        "round_status": state.round_status
                    },
                    "connected": state.dglab.is_connected
                })
            await asyncio.sleep(0.1)
    
    # 启动监控任务
    asyncio.create_task(monitor_strength())
    

# 启动事件
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_background_tasks())