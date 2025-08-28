import json
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

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