import json
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            self._create_default_config()
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "pulse_data": {
                "受伤": [50, 100, 50, 0],
                "烧伤": [100, 50, 100, 50],
                "傻瓜蛋": [200, 200, 200, 200],
                "烟雾弹": [30, 60, 30, 60],
                "死亡": [200, 0, 200, 0]
            },
            "hit": 100,
            "is_voice": 0,
            "voice_A": 50,
            "voice_B": 50
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        self.config = default_config

    def get(self, key: str, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def update(self, key: str, value):
        """更新配置项并保存"""
        self.config[key] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    @property
    def pulse_data(self):
        return self.config["pulse_data"]

    @property
    def hit_strength(self):
        return int(self.config["hit"]) / 100
    