import json
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_path: str = "config/test_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载并验证 JSON 配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 可添加配置验证逻辑（如字段检查）
        return config

    def get(self, key: str, default=None) -> Any:
        """按层级获取配置（如 'instrument.ip'）"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, {})
            if not value and default is not None:
                return default
        return value or default

# 单例模式全局配置
global_config = ConfigManager()