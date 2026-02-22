"""
内存日志环形缓冲区 + WebSocket 广播

提供：
  - LogBuffer: 固定大小的环形缓冲区，保留最近 N 条日志
  - LogBroadcaster: 管理 WebSocket 连接，实时推送新日志
  - BufferHandler: Python logging Handler，将日志写入 LogBuffer 并广播
"""

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any

# ── 环形缓冲区 ──────────────────────────────────────────


class LogBuffer:
    """固定大小的日志环形缓冲区"""

    def __init__(self, maxlen: int = 500):
        self._buffer: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._id_counter = 0

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        self._id_counter += 1
        record["id"] = self._id_counter
        self._buffer.append(record)
        return record

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._buffer)

    def get_recent(self, n: int = 100) -> list[dict[str, Any]]:
        items = list(self._buffer)
        return items[-n:] if len(items) > n else items


# ── WebSocket 广播器 ─────────────────────────────────────


class LogBroadcaster:
    """管理 WebSocket 连接并广播日志消息"""

    def __init__(self):
        self._connections: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._connections.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._connections.discard(queue)

    def broadcast(self, record: dict[str, Any]):
        for queue in list(self._connections):
            try:
                queue.put_nowait(record)
            except asyncio.QueueFull:
                # 消费者太慢，丢弃旧消息
                pass


# ── 全局单例 ──────────────────────────────────────────────

log_buffer = LogBuffer(maxlen=500)
log_broadcaster = LogBroadcaster()


# ── Logging Handler ──────────────────────────────────────


class BufferHandler(logging.Handler):
    """
    Python logging Handler：将日志记录写入 LogBuffer 并通过 WebSocket 广播。
    在 main.py 中添加到根 logger。
    """

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(
                    timespec="milliseconds"
                ),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            }
            log_buffer.append(entry)
            log_broadcaster.broadcast(entry)
        except Exception:
            self.handleError(record)
