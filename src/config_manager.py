import json
from dataclasses import dataclass

@dataclass
class AppConfig:
    client_id: str
    redirect_uri: str
    secret_key: str
    auth_code: str = None
    access_token: str = None

class ConfigManager:
    CONFIG_FILE = "src\config.json"

    @staticmethod
    def load() -> AppConfig:
        with open(ConfigManager.CONFIG_FILE, "r") as f:
            return AppConfig(**json.load(f))

    @staticmethod
    def save(cfg: AppConfig):
        with open(ConfigManager.CONFIG_FILE, "w") as f:
            json.dump(cfg.__dict__, f, indent=4)
