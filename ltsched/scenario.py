import abc
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from functools import partial
from inspect import isawaitable
from itertools import chain
from typing import Awaitable, Callable, ClassVar, Dict, FrozenSet, Iterable, List, Literal, Optional, Tuple, Union

from .model import ScenarioError, ScenarioEvent, ScenarioExecutionStatus, ScenarioTaskName, ScenarioWarning
from .protocols import ScenarioId, ScenarioStore, ScenarioStoreRepo, TaskScheduler, TimePoint


@dataclass
class HandlerResult:
    state: str
    next_event: Optional[ScenarioEvent]
    next_run: Optional[TimePoint] = None


EventHandler = Callable[[ScenarioEvent], Union[HandlerResult, Awaitable[HandlerResult]]]
TransitionHandler = Callable[[], None]


@dataclass
class EventHandlerDescriptor:
    events: Tuple[str]
    in_state: Tuple[str]
    out_state: Union[Literal['*'], FrozenSet[str]]


TransitionState = Union[str, Iterable[str], Enum, Iterable[Enum]]
Transition = Tuple[TransitionState, TransitionState]


def to_str(value: Union[str, Enum]) -> str:
    return value if isinstance(value, str) else value.value


def to_str_list(value: Iterable[Union[str, Enum]]) -> List[str]:
    try:
        # noinspection PyUnresolvedReferences
        return [it.strip() for it in value.split(',')]
    except AttributeError:
        # noinspection PyTypeChecker
        return [to_str(it) for it in value] if isinstance(value, Iterable) else [to_str(value)]


def event_handler(events: Union[str, Enum, Iterable[str], Iterable[Enum]],
                  transitions: Iterable[Transition]):
    def inner(method):
        in_state = set()
        out_state = set()
        for transition in transitions:
            assert len(transition) == 2, "Transition descriptor must have 'in' and 'out' states"
            in_state |= set(to_str_list(transition[0]))
            out_state |= set(to_str_list(transition[1]))
        method.__events__ = EventHandlerDescriptor(events=tuple(to_str_list(events)),
                                                   in_state=('*',) if '*' in in_state else tuple(in_state),
                                                   out_state='*' if '*' in out_state else frozenset(out_state))
        return method

    return inner


@dataclass
class TransitionHandlerDescriptor:
    states: Tuple[str]
    on_exit: bool


def _on_transition(state: TransitionState, run_on_exit: bool):
    def inner(method):
        states = set(chain(to_str_list(state)))
        method.__transitions__ = TransitionHandlerDescriptor(states=tuple(states), on_exit=run_on_exit)
        return method

    return inner


on_enter = partial(_on_transition, run_on_exit=False)
on_exit = partial(_on_transition, run_on_exit=True)
EventHandlersRegistry = Dict[str, Dict[str, EventHandler]]
TransitionHandlersRegistry = Dict[str, List[TransitionHandler]]


class ScenarioMeta(abc.ABCMeta):

    def __new__(mcs, name, bases, namespace, **kwargs):
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        event_handlers = defaultdict(dict)
        transition_handlers = defaultdict(dict)
        for base in bases:
            base_event_handlers = getattr(base, 'event_handlers', None)
            if base_event_handlers:
                event_handlers |= base_event_handlers
            base_transition_handlers = getattr(base, 'transition_handlers', None)
            if base_transition_handlers:
                transition_handlers |= {k: {it.__name__: it for it in v}
                                        for k, v in base_transition_handlers.items()}
        for attr in cls.__dict__.values():
            if hasattr(attr, '__events__'):
                mcs.register_event_handler(event_handlers, attr)
            if hasattr(attr, '__transitions__'):
                mcs.register_transition_handler(transition_handlers, attr)
        cls.event_handlers = event_handlers
        cls.transition_handlers = {k: list(v.values()) for k, v in transition_handlers.items()}
        return cls

    @staticmethod
    def register_event_handler(registry: EventHandlersRegistry, handler: EventHandler) -> None:
        handler_descr: EventHandlerDescriptor = getattr(handler, '__events__')
        for state in handler_descr.in_state:
            for event_type in handler_descr.events:
                registry[state][event_type] = handler

    @staticmethod
    def register_transition_handler(registry: Dict[str, Dict[str, TransitionHandler]],
                                    handler: TransitionHandler) -> None:
        # noinspection PyUnresolvedReferences
        handler_descr: TransitionHandlerDescriptor = handler.__transitions__
        for state in handler_descr.states:
            registry[state][handler.__name__] = handler


class Scenario(metaclass=ScenarioMeta):
    name: ClassVar[str]
    start_state: ClassVar[str]
    end_states: ClassVar[FrozenSet[str]]
    event_handlers: ClassVar[EventHandlersRegistry]  # {state: {event: handler}}
    transition_handlers: ClassVar[TransitionHandlersRegistry]  # {state: [handler]}
    store: Optional[ScenarioStore]
    scenario_id: Optional[ScenarioId]

    def __init__(self, scheduler: TaskScheduler, store_repo: ScenarioStoreRepo):
        self.scheduler = scheduler
        self.store_repo = store_repo
        self.store = None
        self.scenario_id = None

    def __str__(self):
        return f'{self.__class__.name}({self.name}):{self.scenario_id}'

    async def read_store(self) -> None:
        self.store = await self.store_repo.read_store(self.scenario_id)
        if not self.store:
            raise ScenarioError(f'Stored data for {self} not found')

    async def write_store(self) -> None:
        await self.store_repo.write_store(self.scenario_id, self.store)

    def get_event_handler(self, event: ScenarioEvent) -> Optional[EventHandler]:
        event_type = event if isinstance(event, str) else event.type
        state_events = self.event_handlers.get(self.store.state)
        if not state_events:
            state_events = self.event_handlers.get('*')
        if state_events:
            handler = state_events.get(event_type)
            if not handler:
                handler = state_events.get('*')
            return handler

    async def run(self, scenario_id: ScenarioId, event: ScenarioEvent):
        self.scenario_id = scenario_id
        await self.read_store()
        if self.store.exec_state != ScenarioExecutionStatus.Run:
            return
        prior_state = self.store.state
        handler = self.get_event_handler(event)
        if handler:
            result_or_awaitable = handler(event)
            result: HandlerResult = await result_or_awaitable \
                if isawaitable(result_or_awaitable) else result_or_awaitable
            self.check_new_state(handler, result.state)
            if result.state != prior_state:
                await self.run_transition_handlers(prior_state, True)
            self.store.state = result.state
            if result.state != prior_state:
                await self.run_transition_handlers(result.state, False)
            if result.state in self.end_states:
                self.store.exec_state = ScenarioExecutionStatus.Finished
            await self.write_store()
            await self.schedule_next_run(result)
        else:
            raise ScenarioWarning(f'Not found handler for event %s in scenario %s', event, self.name)

    async def schedule_next_run(self, result: HandlerResult):
        if self.store.exec_state == ScenarioExecutionStatus.Run:
            return
        elif result.next_event:
            task_name = ScenarioTaskName % self.name
            await self.scheduler.schedule(result.next_run,
                                          task_name,
                                          self.scenario_id,
                                          result.next_event,
                                          task_id=f'{task_name}:{self.scenario_id}',
                                          force=True)

    def check_new_state(self, handler: EventHandler, state: str) -> None:
        # noinspection PyUnresolvedReferences
        descr: EventHandlerDescriptor = handler.__events__
        if descr.out_state != '*' and state not in descr.out_state:
            raise ScenarioWarning(f'Event handler {handler.__name__} in {self} return not allowed state "{state}"')

    async def run_transition_handlers(self, state: str, run_on_exit: bool):
        handlers = self.transition_handlers.get(state, [])
        handlers.extend(self.transition_handlers.get('*', []))
        for handler in handlers:
            descr: TransitionHandlerDescriptor = handler.__transitions__
            if descr.on_exit == run_on_exit:
                result_or_awaitable = handler()
                if isawaitable(result_or_awaitable):
                    await result_or_awaitable
