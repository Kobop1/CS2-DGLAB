from aiohttp import web
import asyncio

class GameStateListener:
    def __init__(self, config_manager, command_queue, dglab_controller):
        self.config = config_manager
        self.command_queue = command_queue
        self.health = 0  # 初始血量
        self.app = self._create_app()
        self.player_status = "正常"
        self.round_status = "准备中"
        self.dglab_controller = dglab_controller
        
        # 挑战模式相关变量
        self.challenge_mode_current_strength = 0
        self.kills = 0  # 击杀数
        self.last_kills = 0  # 上次击杀数

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
        # 根据模式选择处理方式
        mode = self.config.get("mode", "normal")
        if mode == "fixed":
            await self._process_player_state_fixed_mode(data)
        elif mode == "challenge":
            await self._process_player_state_challenge_mode(data)
        else:
            await self._process_player_state_normal_mode(data)

    async def _process_player_state_normal_mode(self, data):
        """处理普通模式下的玩家状态数据"""
        player_data = data["player"]
        now_health = player_data["state"]["health"]
        flash = player_data["state"]["flashed"]
        smoke = player_data["state"]["smoked"]
        burning = player_data["state"]["burning"]
        
        # 更新状态显示
        self._update_status_text(now_health, flash, smoke, burning, data)
        
        # 处理血量变化（受伤效果）
        if now_health < self.health and self.config.get("enable_hit", 1) == 1:
            await self._handle_health_change_normal(now_health)
        
        # 处理异常状态（添加开关判断）
        if flash > 0 and self.config.get("enable_flash", 1) == 1:
            await self._send_pulse_normal("傻瓜蛋")
        if smoke > 0 and self.config.get("enable_smoke", 1) == 1:
            await self._send_pulse_normal("烟雾弹")
        if burning > 0 and self.config.get("enable_burn", 1) == 1:
            await self._send_pulse_normal("烧伤")

        # 处理死亡状态（添加开关判断）
        if now_health == 0 and self.health > 0 and self.config.get("enable_death", 1) == 1:
            await self._handle_death_normal()
        else:
            self.health = now_health
            
        # 处理回合状态
        await self._handle_round_status_normal(data)

    async def _process_player_state_fixed_mode(self, data):
        """处理固定强度模式下的玩家状态数据"""
        player_data = data["player"]
        now_health = player_data["state"]["health"]
        flash = player_data["state"]["flashed"]
        smoke = player_data["state"]["smoked"]
        burning = player_data["state"]["burning"]
        
        # 更新状态显示
        self._update_status_text(now_health, flash, smoke, burning, data)
        
        # 处理血量变化（受伤效果）
        if now_health < self.health and self.config.get("enable_hit", 1) == 1:
            await self._handle_health_change_fixed(now_health)
        
        # 处理异常状态（添加开关判断）
        if flash > 0 and self.config.get("enable_flash", 1) == 1:
            await self._send_pulse_fixed("傻瓜蛋")
        if smoke > 0 and self.config.get("enable_smoke", 1) == 1:
            await self._send_pulse_fixed("烟雾弹")
        if burning > 0 and self.config.get("enable_burn", 1) == 1:
            await self._send_pulse_fixed("烧伤")

        # 处理死亡状态（添加开关判断）
        if now_health == 0 and self.health > 0 and self.config.get("enable_death", 1) == 1:
            await self._handle_death_fixed()
        else:
            self.health = now_health
            
        # 处理回合状态
        await self._handle_round_status_fixed(data)

    async def _process_player_state_challenge_mode(self, data):
        if "player" not in data or "state" not in data["player"]:
            # 当检测不到state数据时重置挑战模式相关数据
            self.challenge_mode_current_strength = 0
            self.kills = 0
            self.last_kills = 0
            self.health = 0
            return
        """处理挑战模式下的玩家状态数据"""
        player_data = data["player"]
        now_health = player_data["state"]["health"]
        flash = player_data["state"]["flashed"]
        smoke = player_data["state"]["smoked"]
        burning = player_data["state"]["burning"]
        
        # 初始化挑战模式强度
        if self.challenge_mode_current_strength == 0:
            self.challenge_mode_current_strength = int(self.config.get("challenge_mode_initial_strength", 30))
            await self._set_strength_by_percentage(self.challenge_mode_current_strength)
        
        # 更新状态显示
        self._update_status_text(now_health, flash, smoke, burning, data)
        
        # 处理击杀数变化（挑战模式）
        if "state" in player_data and "round_kills" in player_data["state"]:
            current_kills = player_data["state"]["round_kills"]
            if current_kills > self.last_kills:
                # 玩家击杀增加，减少强度
                kill_reduction = int(self.config.get("challenge_mode_kill_reduction", 10))
                self.challenge_mode_current_strength = max(10, self.challenge_mode_current_strength - kill_reduction)
                await self._set_strength_by_percentage(self.challenge_mode_current_strength)
                self.last_kills = current_kills
                self.kills = current_kills
            elif current_kills < self.last_kills:
                # 玩家击杀减少（可能是回合重置），更新击杀数
                self.last_kills = current_kills
                self.kills = current_kills
        
        # 处理血量变化（受伤效果）
        if now_health < self.health and self.config.get("enable_hit", 1) == 1:
            await self._handle_health_change_challenge(now_health)
        
        # 处理异常状态（添加开关判断）
        if flash > 0 and self.config.get("enable_flash", 1) == 1:
            await self._send_pulse_challenge("傻瓜蛋")
        if smoke > 0 and self.config.get("enable_smoke", 1) == 1:
            await self._send_pulse_challenge("烟雾弹")
        if burning > 0 and self.config.get("enable_burn", 1) == 1:
            await self._send_pulse_challenge("烧伤")

        # 处理死亡状态（添加开关判断）
        if now_health == 0 and self.health > 0 and self.config.get("enable_death", 1) == 1:
            await self._handle_death_challenge()
        else:
            self.health = now_health
            
        # 处理回合状态
        await self._handle_round_status_challenge(data)

    async def _handle_health_change_normal(self, new_health):
        """普通模式下处理血量变化"""
        health_loss = self.health - new_health
        
        # 发送受伤波形
        await self._send_pulse_normal("受伤")
        
        # 调整强度
        await self._adjust_strength(health_loss)

    async def _handle_health_change_fixed(self, new_health):
        """固定强度模式下处理血量变化"""
        health_loss = self.health - new_health
        
        # 发送受伤波形（使用固定强度）
        fixed_strength = int(self.config.get("fixed_mode_strength", 50))
        await self._send_pulse_with_fixed_strength("受伤", fixed_strength)

    async def _handle_health_change_challenge(self, new_health):
        """挑战模式下处理血量变化"""
        health_loss = self.health - new_health
        
        # 发送受伤波形
        await self._send_pulse_challenge("受伤")
        
        # 挑战模式下不需要根据血量损失调整强度，使用固定强度
        # await self._adjust_strength(health_loss)

    async def _send_pulse_normal(self, pulse_type):
        """普通模式下发送指定类型的波形"""
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data[pulse_type]
        })

    async def _send_pulse_fixed(self, pulse_type):
        """固定强度模式下发送指定类型的波形"""
        fixed_strength = int(self.config.get("fixed_mode_strength", 50))
        await self._send_pulse_with_fixed_strength(pulse_type, fixed_strength)

    async def _send_pulse_challenge(self, pulse_type):
        """挑战模式下发送指定类型的波形"""
        # 使用当前挑战模式的强度发送波形
        await self._set_strength_by_percentage(self.challenge_mode_current_strength)
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data[pulse_type]
        })

    async def _send_pulse_with_fixed_strength(self, pulse_type, strength_percentage):
        """在固定强度模式下发送指定类型的波形"""
        # 先设置固定强度
        await self._set_strength_by_percentage(strength_percentage)
        
        # 然后发送波形
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data[pulse_type]
        })

    async def _adjust_strength(self, health_loss):
        """根据血量损失调整强度"""
        base_ratio = int(health_loss * self.config.hit_strength)

        strength_a = int(base_ratio * self.dglab_controller.max_strength_A / 100)
        strength_b = int(base_ratio * self.dglab_controller.max_strength_B / 100)

        strength_a = min(strength_a, self.dglab_controller.max_strength_A)
        strength_b = min(strength_b, self.dglab_controller.max_strength_B)

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

    async def _set_strength_by_percentage(self, percentage):
        """根据百分比设置强度"""
        strength_a = int(self.dglab_controller.max_strength_A * percentage / 100)
        strength_b = int(self.dglab_controller.max_strength_B * percentage / 100)
        
        await self.command_queue.put({
            "type": "strlst", 
            "data": strength_a, 
            "chose": "a"
        })
        await self.command_queue.put({
            "type": "strlst", 
            "data": strength_b, 
            "chose": "b"
        })

    async def _handle_death_normal(self):
        """普通模式下处理死亡状态"""
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data["死亡"]
        })
        await asyncio.sleep(1)
        await self.command_queue.put({"type": "strlse", "data": 100})
        await asyncio.sleep(5)
        self.health = 100  # 重置血量

    async def _handle_death_fixed(self):
        """固定强度模式下处理死亡状态"""
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data["死亡"]
        })
        await asyncio.sleep(1)
        # 固定模式下死亡不重置强度
        await asyncio.sleep(5)
        self.health = 100  # 重置血量

    async def _handle_death_challenge(self):
        """挑战模式下处理死亡状态"""
        await self.command_queue.put({
            "type": "pluse", 
            "data": self.config.pulse_data["死亡"]
        })
        await asyncio.sleep(1)
        
        # 挑战模式下死亡，增加强度
        death_boost = int(self.config.get("challenge_mode_death_boost", 20))
        self.challenge_mode_current_strength = min(100, self.challenge_mode_current_strength + death_boost)
        await self._set_strength_by_percentage(self.challenge_mode_current_strength)
            
        await asyncio.sleep(5)
        self.health = 100  # 重置血量

    async def _handle_round_status_normal(self, data):
        """普通模式下处理回合状态"""
        if "round" in data:
            if data["round"]["phase"] == "over":
                await self.command_queue.put({"type": "strlse", "data": 100})
            # 处理游戏结束
            if data["map"]["phase"] == "gameover":
                await self.command_queue.put({"type": "strlse", "data": 100})

    async def _handle_round_status_fixed(self, data):
        """固定强度模式下处理回合状态"""
        if "round" in data:
            if data["round"]["phase"] == "over":
                # 固定强度模式不重置强度
                pass
            # 处理游戏结束
            if data["map"]["phase"] == "gameover":
                # 固定强度模式不重置强度
                pass

    async def _handle_round_status_challenge(self, data):
        """挑战模式下处理回合状态"""
        if "round" in data:
            if data["round"]["phase"] == "over":
                # 挑战模式下回合结束不重置强度
                pass
            # 处理游戏结束
            if data["map"]["phase"] == "gameover":
                # 挑战模式下游戏结束不重置强度
                pass

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