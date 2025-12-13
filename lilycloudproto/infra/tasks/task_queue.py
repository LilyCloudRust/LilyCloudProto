import asyncio
from dataclasses import dataclass


@dataclass
class TaskPayload:
    task_id: int


class TaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[TaskPayload] = asyncio.Queue()

    async def enqueue(self, task_id: int) -> None:
        """Add a task ID to the processing queue."""
        await self._queue.put(TaskPayload(task_id=task_id))

    async def dequeue(self) -> TaskPayload:
        """Get the next task ID to process."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark the current task as completed."""
        self._queue.task_done()


task_queue = TaskQueue()
