from aiohttp import web
import asyncio

class GameStateListener:
    def __init__(self, config_manager, command_queue,dglab_controller):
        self.config = config_manager
        self.command_queue = command_queue
        self.health = 0  # 初始血量
        self.app = self._create_app()
        self.player_status = "正常"
        self.round_status = "准备中"
        self.dglab_controller = dglab_controller

    def _create_app(self):
        """创建HTTP应用"""
        app = web.Application()
        app["queue"] = self.command_queue
        app.router.add_post("", self.handle_game_state)
        return app

    async def start(self, host: str = "127.0.0.1", port: int = 3000):
        """启动HTTP服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"游戏状态监听服务器已启动: http://{host}:{port}")

    async def handle_game_state(self, request):
        """处理游戏状态POST请求"""
        try:
            data = await request.json()
            if not data:
                return web.json_response({"status": "error", "message": "空请求"}, status=400)

            # 验证数据格式
            if "player" not in data or "map" not in data:
                return web.json_response({"status": "error", "message": "数据格式错误"}, status=400)
            #必须为当前玩家状态才处理
            if data["provider"]["steamid"] == data["player"]["steamid"]:
                # 处理玩家状态
                await self._process_player_state(data)
                return web.json_response({"status": "success"})
        except Exception as e:
            print(f"处理游戏状态出错: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _process_player_state(self, data):
        """处理玩家状态数据"""
        player_data = data["player"]
        now_health = player_data["state"]["health"]
        flash = player_data["state"]["flashed"]
        smoke = player_data["state"]["smoked"]
        burning = player_data["state"]["burning"]
        # 更新状态显示
        self._update_status_text(now_health, flash, smoke, burning, data)
        # 处理血量变化（受伤效果）
        if now_health < self.health and self.config.get("enable_hit", 1) == 1:
            await self._handle_health_change(now_health)
        
        # 处理异常状态（添加开关判断）
        if flash > 0 and self.config.get("enable_flash", 1) == 1:
            await self.command_queue.put({
                "type": "pluse", 
                "data": self.config.pulse_data["傻瓜蛋"]
            })
        if smoke > 0 and self.config.get("enable_smoke", 1) == 1:
            await self.command_queue.put({
                "type": "pluse", 
                "data": self.config.pulse_data["烟雾弹"]
            })
        if burning > 0 and self.config.get("enable_burn", 1) == 1:
            await self.command_queue.put({
                "type": "pluse", 
                "data": self.config.pulse_data["烧伤"]
            })

        # 处理死亡状态（添加开关判断）
        if now_health == 0 and self.health > 0 and self.config.get("enable_death", 1) == 1:
            await self.command_queue.put({
                "type": "pluse", 
                "data": self.config.pulse_data["死亡"]
            })
            await asyncio.sleep(1)
            await self.command_queue.put({"type": "strlse", "data": 100})
            await asyncio.sleep(5)
            self.health = 100  # 重置血量
        else:
            self.health = now_health
        if "round" in data:
            if data["round"]["phase"] == "over":
                await self.command_queue.put({"type": "strlse", "data": 100})
            # 处理游戏结束
            if data["map"]["phase"] == "gameover":
                await self.command_queue.put({"type": "strlse", "data": 100})
    async def _handle_health_change(self, new_health):
        health_loss = self.health - new_health
        base_ratio = int(health_loss * self.config.hit_strength)  # 这是相对比例（如18）


        strength_a = int(base_ratio * self.dglab_controller.max_strength_A / 100)
        strength_b = int(base_ratio * self.dglab_controller.max_strength_B / 100)

        strength_a = min(strength_a, self.dglab_controller.max_strength_A)
        strength_b = min(strength_b, self.dglab_controller.max_strength_B)

        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data["受伤"]
        })

        # 发送强度调整
        await self.command_queue.put({
            "type": "strlup", 
            "data": strength_a, 
            "chose": "a"
        })
        await self.command_queue.put({
            "type": "strlup", 
            "data": strength_b, 
            "chose": "b"
        })

    def _update_status_text(self, health, flash, smoke, burning, data):
        """更新状态文本描述"""
        status_parts = []
        if flash > 0:
            status_parts.append("被闪光")
        if smoke > 0:
            status_parts.append("被烟雾")
        if burning > 0:
            status_parts.append("被烧伤")
            
        if health == 0:
            self.player_status = "已死亡"
        elif status_parts:
            self.player_status = ", ".join(status_parts)
        else:
            self.player_status = "正常"
            
        # 更新回合状态
        if "round" in data:
            self.round_status = data["round"]["phase"]
    