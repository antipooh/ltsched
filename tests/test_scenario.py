from enum import Enum

import pytest

from ltsched.model import BaseScenarioEventObject, Scenario, event_handler
from ltsched.protocols import TaskScheduler


class FakeState(Enum):
    WaitSignal = 'wait-signal'
    WaitFlag = 'wait-flag'
    Error = 'error'
    Closed = 'closed'


class FlagEvent(BaseScenarioEventObject):
    name = 'flag'


class FakeScenario(Scenario):
    name = 'fake'
    start_state = FakeState.WaitSignal
    end_states = frozenset((FakeState.Error, FakeState.Closed))

    @event_handler('signal', ())
    async def on_signal(self, event: str):
        print('on_signal')

    @event_handler(FlagEvent, ())
    async def check_flag(self, event: str):
        print('check_flag')


@pytest.fixture
def scenario(mocker):
    return FakeScenario(mocker.AsyncMock(spec=TaskScheduler))
