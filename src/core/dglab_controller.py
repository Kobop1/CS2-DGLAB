import asyncio
import os
import sys
from pydglab_ws import (
    Channel,
    RetCode,
    DGLabWSServer,
    StrengthOperationType,
    StrengthData,
    FeedbackButton
)

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的路径
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境路径
    return os.path.join(os.path.abspath("."), relative_path)

class DGLabController:
    def __init__(self, ip_address: str):
        self.ip_address = ip_address
        self.server = None
        self.client = None
        self.queue = asyncio.Queue()
        self.max_strength_A = 0
        self.max_strength_B = 0
        self.current_strength_A = 0
        self.current_strength_B = 0
        self.is_connected = False

    async def start(self):
        """启动DGLab WebSocket服务器"""
        self.server = DGLabWSServer("0.0.0.0", 5678, 60)
        self.client = self.server.new_local_client()
    
        async with self.server:
            print(f"已启动DGLab WebSocket服务器，等待客户端连接...")
            await self._handle_client()

    async def _handle_client(self):
        """处理客户端连接和数据接收"""
        # 等待绑定
        await self.client.bind()
        self.is_connected = True
        print(f"已与DGLab设备 {self.client.target_id} 绑定")
        
        # 启动队列监听任务
        queue_task = asyncio.create_task(self._process_queue())
        
        # 监听设备数据
        async for data in self.client.data_generator():
            await self._process_device_data(data)
        
        # 清理任务
        queue_task.cancel()
        await queue_task

    async def _process_device_data(self, data):
        """处理从设备接收的数据"""
        if isinstance(data, StrengthData):
            self.max_strength_A = data.a_limit
            self.max_strength_B = data.b_limit
            self.current_strength_A = data.a
            self.current_strength_B = data.b
        elif isinstance(data, FeedbackButton):
            print(f"收到设备按钮事件: {data.name}")
        elif data == RetCode.CLIENT_DISCONNECTED:
            print("设备已断开连接，尝试重新绑定...")
            self.is_connected = False
            await self.client.rebind()
            self.is_connected = True

    async def _process_queue(self):
        """处理指令队列"""
        while True:
            waveform_data = await self.queue.get()
            await self._execute_command(waveform_data)
            self.queue.task_done()

    async def _execute_command(self, cmd):
        """执行振动指令"""
        if not self.client or not self.is_connected:
            return
        cmd_type = cmd["type"]
        data = cmd["data"]
        
        if cmd_type == "pluse":
            await self.client.add_pulses(Channel.A, *(data * 1))
            await self.client.add_pulses(Channel.B, *(data * 1))
        elif cmd_type == "strlup":
            channel = Channel.A if cmd["chose"] == "a" else Channel.B
            await self.client.set_strength(channel, StrengthOperationType.INCREASE, data)
        elif cmd_type == "strlse":
            await self.client.set_strength(Channel.A, StrengthOperationType.DECREASE, 200)
            await self.client.set_strength(Channel.B, StrengthOperationType.DECREASE, 200)
        elif cmd_type == "strlst":
            channel = Channel.A if cmd["chose"] == "a" else Channel.B
            await self.client.set_strength(channel, StrengthOperationType.SET_TO, data)

    async def send_command(self, cmd):
        """发送指令到队列"""
        await self.queue.put(cmd)