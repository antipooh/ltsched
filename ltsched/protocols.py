
from datetime import datetime, timedelta
from typing import Optional, Protocol, Union

TimePoint = Union[None, datetime, timedelta]


class TaskScheduler(Protocol):

    async def schedule(self, point: TimePoint, task_name: str, *args,
                       task_id: Optional[str] = None, force: bool = False) -> None:
        ...
