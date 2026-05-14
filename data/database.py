"""
数据库连接和配置
"""

import os
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from config.settings import get_settings

# 获取设置
settings = get_settings()

# 创建基类
Base = declarative_base()

# 全局引擎和会话工厂
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine(database_url: Optional[str] = None) -> Engine:
    """
    获取数据库引擎

    Args:
        database_url: 数据库URL，如果为None则使用设置中的URL

    Returns:
        SQLAlchemy引擎
    """
    global _engine

    if _engine is not None:
        return _engine

    if database_url is None:
        database_url = settings.database_url

    # 如果是SQLite，确保数据库文件目录存在
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        db_file = Path(db_path)

        # 确保目录存在
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # 对于SQLite，使用StaticPool以避免多线程问题
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
            poolclass=StaticPool if "sqlite" in database_url else None,
            echo=False,  # 设置为True以查看SQL语句
        )
    else:
        # 其他数据库（如PostgreSQL）
        _engine = create_engine(
            database_url,
            pool_pre_ping=True,  # 连接前ping检查
            pool_recycle=3600,  # 连接回收时间（秒）
        )

    return _engine


def get_session(engine: Optional[Engine] = None) -> Session:
    """
    获取数据库会话

    Args:
        engine: 数据库引擎，如果为None则使用全局引擎

    Returns:
        SQLAlchemy会话
    """
    global _SessionLocal

    if engine is None:
        engine = get_engine()

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

    return _SessionLocal()


def init_database(engine: Optional[Engine] = None):
    """
    初始化数据库（创建所有表）

    Args:
        engine: 数据库引擎
    """
    if engine is None:
        engine = get_engine()

    # 导入所有模型以确保它们被注册
    from . import models  # noqa: F401

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 初始化默认数据
    _init_default_data(engine)


def _init_default_data(engine: Engine):
    """
    初始化默认数据

    Args:
        engine: 数据库引擎
    """
    from .models import SeedType
    from .seed_types import SeedTypeManager

    session = get_session(engine)

    try:
        # 检查是否已有数据
        count = session.query(SeedType).count()
        if count == 0:
            # 添加默认籽源类型
            seed_manager = SeedTypeManager(session)
            seed_manager.add_default_seed_types()
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"初始化默认数据时出错: {e}")
    finally:
        session.close()


def drop_database(engine: Optional[Engine] = None):
    """
    删除所有表（谨慎使用！）

    Args:
        engine: 数据库引擎
    """
    if engine is None:
        engine = get_engine()

    # 导入所有模型以确保它们被注册
    from . import models  # noqa: F401

    # 删除所有表
    Base.metadata.drop_all(bind=engine)


def reset_database(engine: Optional[Engine] = None):
    """
    重置数据库（删除所有表并重新创建）

    Args:
        engine: 数据库引擎
    """
    if engine is None:
        engine = get_engine()

    drop_database(engine)
    init_database(engine)


def get_database_info(engine: Optional[Engine] = None) -> dict:
    """
    获取数据库信息

    Args:
        engine: 数据库引擎

    Returns:
        包含数据库信息的字典
    """
    if engine is None:
        engine = get_engine()

    from .models import SeedType, MonteCarloResult, TreatmentPlan

    session = get_session(engine)

    try:
        info = {
            "database_url": str(engine.url),
            "seed_types_count": session.query(SeedType).count(),
            "monte_carlo_results_count": session.query(MonteCarloResult).count(),
            "treatment_plans_count": session.query(TreatmentPlan).count(),
            "tables": list(Base.metadata.tables.keys()),
        }

        # 如果是SQLite，添加文件信息
        if engine.url.drivername == "sqlite":
            db_path = engine.url.database
            if db_path and os.path.exists(db_path):
                info["database_size"] = os.path.getsize(db_path)
                info["database_path"] = db_path

        return info
    finally:
        session.close()


# 上下文管理器用于数据库会话
class DatabaseSession:
    """数据库会话上下文管理器"""

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine
        self.session = None

    def __enter__(self) -> Session:
        self.session = get_session(self.engine)
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()


# 便捷函数
def with_session(func):
    """装饰器：为函数提供数据库会话"""

    def wrapper(*args, **kwargs):
        with DatabaseSession() as session:
            return func(session, *args, **kwargs)

    return wrapper