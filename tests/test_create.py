from enum import Enum

import pytest

from ltsched.model import Scenario, event_handler, on_enter, on_exit, to_str_list


class FakeState(Enum):
    State1 = 'state1'
    State2 = 'state2'
    State3 = 'state3'


class FakeEnum(Enum):
    Event1 = 'event1'
    Event2 = 'event2'


@pytest.mark.parametrize('input, result', (
        ('state2', ['state2']),
        ('state2, state3', ['state2', 'state3']),
        (('state2',), ['state2']),
        (('state2', 'state3'), ['state2', 'state3']),
        (FakeState.State1, ['state1']),
        ((FakeState.State1, FakeState.State2), ['state1', 'state2']),
))
def test_to_str_list(input, result):
    assert to_str_list(input) == result


def test_registry_event_handlers():
    class FakeScenario(Scenario):

        @event_handler(FakeEnum.Event1, [('*', 'state2, state3')])
        async def handler1(self, *args):
            pass

        @event_handler('*', [('state2', (FakeState.State1, FakeState.State3))])
        async def handler2(self, *args):
            pass

    assert FakeScenario.event_handlers['*']['event1'] == FakeScenario.handler1
    assert FakeScenario.event_handlers['state2']['*'] == FakeScenario.handler2


def test_inherited_event_handlers():
    class ParentScenario(Scenario):

        @event_handler('signal1', [('state1', 'state2, state3')])
        async def handler1(self, *args):
            pass

        @event_handler('signal2', [('state3', 'state3')])
        async def handler2(self, *args):
            pass

    class ChildScenario(ParentScenario):

        @event_handler('signal2', [('state3', 'state4')])
        async def handler1(self, *args):
            pass

        @event_handler('signal3', [('state1', 'state2, state3')])
        async def handler2(self, *args):
            pass

    assert ParentScenario.event_handlers['state1']['signal1'] == ParentScenario.handler1
    assert ChildScenario.event_handlers['state3']['signal2'] == ChildScenario.handler1
    assert ChildScenario.event_handlers['state1']['signal3'] == ChildScenario.handler2


def test_registry_transition_handlers():
    class FakeScenario(Scenario):

        @on_exit('state2, state3')
        async def handler1(self, *args):
            pass

        @on_enter('*')
        async def handler2(self, *args):
            pass

        @on_exit((FakeState.State1, FakeState.State3))
        async def handler3(self, *args):
            pass

    assert FakeScenario.transition_handlers['state1'] == [FakeScenario.handler3]
    assert FakeScenario.transition_handlers['state2'] == [FakeScenario.handler1]
    assert FakeScenario.transition_handlers['state3'] == [FakeScenario.handler1, FakeScenario.handler3]
    assert FakeScenario.transition_handlers['*'] == [FakeScenario.handler2]
    assert FakeScenario.handler1.__transitions__.on_exit is True
    assert FakeScenario.handler2.__transitions__.on_exit is False
    assert FakeScenario.handler3.__transitions__.on_exit is True
