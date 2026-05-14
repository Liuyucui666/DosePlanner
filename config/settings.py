"""
应用程序设置管理
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """应用程序设置"""

    # 应用程序信息
    app_name: str = Field(default="Dose Planner", env="APP_NAME")
    app_version: str = Field(default="0.1.0", env="APP_VERSION")

    # 数据库配置
    database_url: str = Field(
        default="sqlite:///data/dose_planner.db",
        env="DATABASE_URL"
    )

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")

    # 数据目录
    data_dir: Path = Field(default=Path("./data"), env="DATA_DIR")
    seeds_dir: Path = Field(default=Path("./data/seeds"), env="SEEDS_DIR")
    ct_images_dir: Path = Field(default=Path("./data/ct_images"), env="CT_IMAGES_DIR")

    # 计算配置
    default_grid_resolution: float = Field(default=1.0, env="DEFAULT_GRID_RESOLUTION")
    default_grid_size: int = Field(default=32, env="DEFAULT_GRID_SIZE")
    use_parallel_processing: bool = Field(default=True, env="USE_PARALLEL_PROCESSING")
    max_workers: int = Field(default=4, env="MAX_WORKERS")

    # 可视化配置
    default_colormap: str = Field(default="viridis", env="DEFAULT_COLORMAP")
    show_isodose_lines: bool = Field(default=True, env="SHOW_ISODOSE_LINES")
    isodose_levels: list = Field(default=[50, 80, 90, 100], env="ISODOSE_LEVELS")

    # 籽源默认参数
    default_seed_activity: float = Field(default=3.0, env="DEFAULT_SEED_ACTIVITY")  # mCi
    default_seed_spacing: float = Field(default=10.0, env="DEFAULT_SEED_SPACING")  # mm

    # 性能配置
    use_memory_mapping: bool = Field(default=True, env="USE_MEMORY_MAPPING")
    cache_dir: Path = Field(default=Path("./cache"), env="CACHE_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            # 优先使用环境变量，然后是初始化设置
            return env_settings, init_settings, file_secret_settings

    @validator("data_dir", "seeds_dir", "ct_images_dir", "cache_dir", pre=True)
    def validate_paths(cls, v):
        """验证路径并转换为Path对象"""
        if isinstance(v, str):
            return Path(v)
        return v

    @validator("isodose_levels", pre=True)
    def parse_isodose_levels(cls, v):
        """解析等剂量线级别"""
        if isinstance(v, str):
            return [float(level.strip()) for level in v.split(",")]
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.data_dir,
            self.seeds_dir,
            self.ct_images_dir,
            self.cache_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_database_path(self) -> Path:
        """获取数据库文件路径"""
        if self.database_url.startswith("sqlite:///"):
            # 提取文件路径
            db_path = self.database_url.replace("sqlite:///", "")
            return Path(db_path)
        return None

    def update_from_dict(self, updates: Dict[str, Any]):
        """从字典更新设置"""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """将设置转换为字典"""
        result = {}
        for field in self.__fields__.values():
            value = getattr(self, field.name)
            if isinstance(value, Path):
                result[field.name] = str(value)
            else:
                result[field.name] = value
        return result

    def save_to_env(self, env_file: Optional[str] = None):
        """保存设置到环境变量文件"""
        if env_file is None:
            env_file = self.Config.env_file

        with open(env_file, "w", encoding="utf-8") as f:
            for key, value in self.to_dict().items():
                if isinstance(value, list):
                    value_str = ",".join(str(v) for v in value)
                else:
                    value_str = str(value)
                f.write(f"{key.upper()}={value_str}\n")


# 全局设置实例
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置实例"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reload_settings() -> Settings:
    """重新加载设置"""
    global _settings_instance
    _settings_instance = Settings()
    return _settings_instance