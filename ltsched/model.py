import abc
from dataclasses import dataclass
from enum import Enum
from inspect import isawaitable
from itertools import chain
from typing import Callable, ClassVar, Dict, FrozenSet, Iterable, NewType, Optional, Tuple, Type, TypeVar, Union

from .protocols import TaskScheduler, TimePoint

ScenarioTaskName = 'run:%s'

ScenarioId = NewType("ScenarioId", str)

ScenarioState = TypeVar("ScenarioState", bound=Enum)
ScenarioStateValue = str


class BaseScenarioStore:
    state: ScenarioState


@dataclass
class BaseScenarioEventObject:
    name: ClassVar[str]


ScenarioEventObject = TypeVar("ScenarioEventObject", bound=BaseScenarioEventObject)
ScenarioStore = TypeVar("ScenarioStore", bound=BaseScenarioStore)
ScenarioEvent = Union[str, ScenarioEventObject]


@dataclass
class HandlerResult:
    state: ScenarioState
    next_event: Optional[ScenarioEvent]
    next_run: Optional[TimePoint] = None


EventHandler = Callable[['Scenario', ScenarioEvent], HandlerResult]


class ScenarioError(Exception):
    pass


class ScenarioWarning(Exception):
    pass


@dataclass
class EventHandlerDescriptor:
    events: Tuple[str]
    in_state: FrozenSet[ScenarioStateValue]
    out_state: FrozenSet[ScenarioStateValue]


ScenarioEventType = Type[ScenarioEventObject]


def collect_events_names(events: Union[str, ScenarioEventType,
                                       Iterable[str], Iterable[ScenarioEventType]]) -> Tuple[str]:
    if isinstance(events, str):
        return events,
    elif hasattr(events, 'name'):
        return events.name,
    else:
        # noinspection PyTypeChecker
        return tuple(it if isinstance(it, str) else getattr(it, 'name') for it in events)


Transition = Tuple[Union[ScenarioStateValue, Iterable[ScenarioStateValue]]]


def str_as_iter(value: Union[str, Iterable[str]]) -> Iterable[str]:
    return (value,) if isinstance(value, ScenarioStateValue) else value


def event_handler(events: Union[str, ScenarioEventType, Iterable[str], Iterable[ScenarioEventType]],
                  transitions: Iterable[Transition]):
    def inner(method):
        method.__events__ = EventHandlerDescriptor(
            events=collect_events_names(events),
            in_state=frozenset(*chain(str_as_iter(it[0]) for it in transitions)),
            out_state=frozenset(*chain(str_as_iter(it[1]) for it in transitions)),
        )
        return method

    return inner


class ScenarioMeta(abc.ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        handlers = {}
        for base in bases:
            base_handlers = getattr(base, 'handlers', None)
            if base_handlers:
                handlers |= base_handlers
        for attr in cls.__dict__.values():
            descr: Optional[EventHandlerDescriptor] = getattr(attr, '__events__', None)
            if descr:
                for name in descr.events:
                    handlers[name] = attr
        cls.handlers = handlers
        return cls


class Scenario(metaclass=ScenarioMeta):
    name: ClassVar[str]
    start_state: ClassVar[ScenarioStateValue]
    end_states: ClassVar[FrozenSet[ScenarioStateValue]]
    handlers: ClassVar[Dict[ScenarioEvent, EventHandler]] = {}
    store: Optional[ScenarioStore]
    scenario_id: Optional[ScenarioId]

    def __init__(self, scheduler: TaskScheduler):
        self.scheduler = scheduler
        self.store = None
        self.scenario_id = None

    @abc.abstractmethod
    async def read_store(self) -> ScenarioStore:
        ...

    @abc.abstractmethod
    async def write_store(self) -> None:
        ...

    async def run(self, scenario_id: ScenarioId, event: ScenarioEvent):
        self.scenario_id = scenario_id
        self.store = await self.read_store()
        handler = self.handlers.get(event)
        if handler:
            result_or_awaitable = handler(event)
            result: HandlerResult = await result_or_awaitable \
                if isawaitable(result_or_awaitable) else result_or_awaitable
            self.store.state = result.state
            await self.write_store()
            await self.schedule_next_run(result)
        else:
            raise ScenarioWarning(f'Not found handler for event %s in scenario %s', event, self.name)

    async def schedule_next_run(self, result: HandlerResult):
        if result.state in self.end_states:
            return
        elif result.next_event:
            task_name = ScenarioTaskName % self.name
            await self.scheduler.schedule(result.next_run,
                                          task_name,
                                          self.scenario_id,
                                          result.next_event,
                                          task_id=f'{task_name}:{self.scenario_id}')
