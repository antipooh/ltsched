from enum import Enum
from typing import cast

import pytest

from ltsched.model import BaseScenarioEventObject, BaseScenarioStore, ScenarioId
from ltsched.protocols import ScenarioStoreRepo, TaskScheduler
from ltsched.scenario import HandlerResult, Scenario, event_handler


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

    @event_handler(Event.Signal, [(FakeState.WaitSignal, FakeState.WaitFlag)])
    def on_signal(self, _):
        return FakeState.WaitFlag.value


@pytest.fixture
def scenario(mocker):
    return FakeScenario(mocker.AsyncMock(spec=TaskScheduler), mocker.AsyncMock(spec=ScenarioStoreRepo))


@pytest.mark.asyncio
async def test_event_handler(scenario, mocker):
    on_event = mocker.Mock(return_value=HandlerResult(state=FakeState.WaitFlag.value))
    scenario.add_event_handler(Event.Signal, [(FakeState.WaitSignal, FakeState.WaitFlag)], on_event)
    scenario.store_repo.read_store.return_value = BaseScenarioStore(state='wait-signal')

    await scenario.run(cast(ScenarioId, 'SCENARIO-ID'), Event.Signal.value)

    on_event.assert_called_with('signal')


@pytest.mark.asyncio
async def test_async_event_handler(scenario, mocker):
    on_event = mocker.AsyncMock(return_value=HandlerResult(state=FakeState.WaitFlag.value))
    scenario.add_event_handler(Event.Signal, [(FakeState.WaitSignal, FakeState.WaitFlag)], on_event)
    scenario.store_repo.read_store.return_value = BaseScenarioStore(state='wait-signal')

    await scenario.run(cast(ScenarioId, 'SCENARIO-ID'), Event.Signal.value)

    on_event.assert_awaited_with('signal')


@pytest.mark.asyncio
async def test_write_changed_state(scenario):
    scenario.store_repo.read_store.return_value = BaseScenarioStore(state='wait-signal')
    scenario_id = cast(ScenarioId, 'SCENARIO-ID')
    await scenario.run(scenario_id, Event.Signal.value)
    scenario.store_repo.write_store.assert_awaited_with(scenario_id,
                                                        BaseScenarioStore(state='wait-flag'))


@pytest.mark.asyncio
async def test_transition_handlers(scenario, mocker):
    scenario.store_repo.read_store.return_value = BaseScenarioStore(state='wait-signal')
    on_enter = mocker.Mock()
    scenario.add_enter_handler('*', on_enter)
    on_exit = mocker.Mock()
    scenario.add_enter_handler('*', on_exit)
    handler2 = mocker.Mock()
    scenario.add_enter_handler(Event.Flag, handler2)

    await scenario.run(cast(ScenarioId, 'SCENARIO-ID'), Event.Signal.value)

    on_enter.assert_called()
    on_exit.assert_called()
    handler2.assert_not_called()


@pytest.mark.asyncio
async def test_async_transition_handlers(scenario, mocker):
    scenario.store_repo.read_store.return_value = BaseScenarioStore(state='wait-signal')
    on_enter = mocker.AsyncMock()
    scenario.add_enter_handler('*', on_enter)
    on_exit = mocker.AsyncMock()
    scenario.add_enter_handler('*', on_exit)
    handler2 = mocker.AsyncMock()
    scenario.add_enter_handler(Event.Flag, handler2)

    await scenario.run(cast(ScenarioId, 'SCENARIO-ID'), Event.Signal.value)

    on_enter.assert_awaited()
    on_exit.assert_awaited()
    handler2.assert_not_called()
