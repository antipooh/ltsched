from datetime import datetime, timedelta
from typing import Iterable, Optional, Protocol, Union

from .model import ScenarioId, ScenarioStore

TimePoint = Union[None, datetime, timedelta]


class TaskScheduler(Protocol):

    async def schedule(self, point: TimePoint, task_name: str, *args,
                       task_id: Optional[str] = None, force: bool = False) -> None:
        ...


class ScenarioStoreRepo(Protocol):

    async def read_store(self, identity: ScenarioId) -> Optional[ScenarioStore]:
        ...

    async def write_store(self, identity: ScenarioId, store: ScenarioStore) -> None:
        ...

    async def search_planned(self, before: datetime) -> Iterable[ScenarioId]:
        ...
