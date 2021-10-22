from enum import Enum

import pytest

from ltsched.model import BaseScenarioEventObject, Scenario, event_handler
from ltsched.protocols import TaskScheduler


class FakeState(Enum):
    WaitSignal = 'wait-signal'
    WaitFlag = 'wait-flag'
    Error = 'error'
    Closed = 'closed'


class Event(Enum):
    Flag = 'flag'
    Signal = 'signal'


class FlagEvent(BaseScenarioEventObject):
    type = Event.Flag


class FakeScenario(Scenario):
    name = 'fake'
    start_state = FakeState.WaitSignal
    end_states = frozenset((FakeState.Error, FakeState.Closed))

    @event_handler(Event.Signal, [(FakeState.WaitSignal, (FakeState.WaitFlag, FakeState.Closed))])
    async def on_signal(self, event: str):
        print('on_signal')

    @event_handler(Event.Flag, [(FakeState.WaitFlag, '*')])
    async def check_flag(self, event: str):
        print('check_flag')


@pytest.fixture
def scenario(mocker):
    return FakeScenario(mocker.AsyncMock(spec=TaskScheduler))
