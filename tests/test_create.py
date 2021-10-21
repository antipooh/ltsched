from ltsched.model import BaseScenarioEventObject, Scenario, event_handler


def test_registry_handlers():
    class Event1(BaseScenarioEventObject):
        name = 'event1'

    class Event2(BaseScenarioEventObject):
        name = 'event2'

    class Event3(BaseScenarioEventObject):
        name = 'event3'

    class FakeScenario(Scenario):

        @event_handler('signal1', ())
        async def handler1(self, *args):
            return 12

        @event_handler(['signal2', 'signal3'], ())
        async def handler2(self, *args):
            pass

        @event_handler(Event1, ())
        async def handler3(self, *args):
            pass

        @event_handler([Event2, Event3], ())
        async def handler4(self, *args):
            pass

    assert FakeScenario.handlers['signal1'] == FakeScenario.handler1
    assert FakeScenario.handlers['signal2'] == FakeScenario.handler2
    assert FakeScenario.handlers['signal3'] == FakeScenario.handler2
    assert FakeScenario.handlers['event1'] == FakeScenario.handler3
    assert FakeScenario.handlers['event2'] == FakeScenario.handler4
    assert FakeScenario.handlers['event3'] == FakeScenario.handler4


def test_inherited_handlers():
    class ParentScenario(Scenario):

        @event_handler('signal1', ())
        async def handler1(self, *args):
            pass

        @event_handler('signal2', ())
        async def handler2(self, *args):
            pass

    class ChildScenario(ParentScenario):

        @event_handler('signal2', ())
        async def handler1(self, *args):
            pass

        @event_handler('signal3', ())
        async def handler2(self, *args):
            pass

    assert ParentScenario.handlers['signal1'] == ParentScenario.handler1
    assert ParentScenario.handlers['signal2'] == ParentScenario.handler2
    assert ChildScenario.handlers['signal1'] == ParentScenario.handler1
    assert ChildScenario.handlers['signal2'] == ChildScenario.handler1
    assert ChildScenario.handlers['signal3'] == ChildScenario.handler2
