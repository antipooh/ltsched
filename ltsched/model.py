from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import (ClassVar, NewType, Optional, TypeVar, Union)

ScenarioTaskName = 'run:%s'

ScenarioId = NewType("ScenarioId", str)


class ScenarioExecutionStatus(Enum):
    Run = 'run'
    Stopped = 'stopped'
    Finished = 'finished'
    Error = 'error'


class BaseScenarioStore:
    exec_state: ScenarioExecutionStatus = ScenarioExecutionStatus.Run
    error: Optional[str] = None
    state: str
    next_run: Optional[datetime] = None


ScenarioStore = TypeVar("ScenarioStore", bound=BaseScenarioStore)


@dataclass
class BaseScenarioEventObject:
    type: ClassVar[str]


ScenarioEventObject = TypeVar("ScenarioEventObject", bound=BaseScenarioEventObject)
ScenarioEvent = Union[str, ScenarioEventObject]


class ScenarioError(Exception):
    pass


class ScenarioWarning(Exception):
    pass
