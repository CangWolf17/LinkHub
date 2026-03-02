"""
SQLAlchemy 异步引擎 & 会话工厂
强制开启 SQLite WAL 模式以解决并发读写锁问题。
"""

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    """每次新建底层连接时，开启 WAL 模式和外键约束。"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入：提供数据库会话，请求结束后自动回滚并关闭。

    事务策略说明:
      - 各路由函数负责在写操作后显式调用 await db.commit()。
      - 此依赖层仅在路由抛出异常时执行 rollback（避免脏数据残留）。
      - 不在 yield 后自动 commit，原因：FastAPI yield 依赖的清理代码
        在 HTTP 响应发出之后异步执行，可能晚于下一个请求的到达，
        导致并发场景下读到未提交数据。
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
