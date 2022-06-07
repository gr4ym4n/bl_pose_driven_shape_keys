
from typing import Iterator, List, Optional, Tuple, Union
from bpy.types import PropertyGroup
from bpy.props import CollectionProperty, IntProperty
from ..lib.events import dataclass, dispatch_event, Event
from .group import PoseDrivenShapeKeyGroup


@dataclass(frozen=True)
class PoseDrivenShapeKeyGroupCreatedEvent(Event):
    group: PoseDrivenShapeKeyGroup


@dataclass(frozen=True)
class PoseDrivenShapeKeyGroupDisposeEvent(Event):
    group: PoseDrivenShapeKeyGroup


@dataclass(frozen=True)
class PoseDrivenShapeKeyTargetRemovedEvent(Event):
    groups: 'PoseDrivenShapeKeyGroups'
    index: int


class PoseDrivenShapeKeyGroups(PropertyGroup):

    active_index: IntProperty(
        name="Target",
        min=0,
        default=0,
        options=set()
        )

    @property
    def active(self) -> Optional[PoseDrivenShapeKeyGroup]:
        index = self.active_index
        return self[index] if index < len(self) else None

    collection__internal__: CollectionProperty(
        type=PoseDrivenShapeKeyGroup,
        options={'HIDDEN'}
        )

    def __contains__(self, key: Union[PoseDrivenShapeKeyGroup, str]) -> bool:
        if isinstance(key, str):
            return self.find(key) != -1
        for item in self:
            if item == key:
                return True
        return False

    def __len__(self) -> int:
        return len(self.collection__internal__)

    def __iter__(self) -> Iterator[PoseDrivenShapeKeyGroup]:
        return iter(self.collection__internal__)

    def __getitem__(self, key: Union[str, int, slice]) -> Union[PoseDrivenShapeKeyGroup, List[PoseDrivenShapeKeyGroup]]:
        return self.collection__internal__[key]

    def find(self, key: str) -> int:
        return self.collection__internal__.find(key)

    def index(self, target: PoseDrivenShapeKeyGroup) -> int:
        if not isinstance(target, PoseDrivenShapeKeyGroup):
            raise TypeError((f'{self.__class__.__name__}.index(target): '
                             f'Expected target to be PoseDrivenShapeKeyGroup,'
                             f' not {target.__class__.__name__}'))
        index = next((i for i,x in enumerate(self) if x == target), -1)
        if index == -1:
            raise ValueError((f'{self.__class__.__name__}.index(target): '
                              f'target {target} is not a member of this collection'))
        return index

    def get(self, name: str, fallback: Optional[object]=None) -> Optional[PoseDrivenShapeKeyGroup]:
        return self.collection__internal__.get(name, fallback)

    def keys(self) -> Iterator[str]:
        return self.collection__internal__.keys()

    def items(self) -> Iterator[Tuple[str, PoseDrivenShapeKeyGroup]]:
        return self.collection__internal__.items()

    def values(self) -> Iterator[PoseDrivenShapeKeyGroup]:
        return self.collection__internal__.values()

    def new(self, name: Optional[str]="PoseTarget") -> PoseDrivenShapeKeyGroup:
        names = list(self.collection__internal__.keys())
        index = 0
        value = name
        while value in names:
            index += 1
            value = f'{value}.{str(index).zfill(3)}'

        group = self.collection__internal__.add()
        group.__init__(name=value)
        dispatch_event(PoseDrivenShapeKeyGroupCreatedEvent(group))

        return group

    def remove(self, group: PoseDrivenShapeKeyGroup) -> None:
        if not isinstance(group, PoseDrivenShapeKeyGroup):
            raise TypeError((f'{self.__class__.__name__}.remove(group): '
                             f'Expected group to be PoseDrivenShapeKeyGroup,'
                             f' not {group.__class__.__name__}'))

        index = next((i for i, x in enumerate(self) if x == group), -1)
        if index == -1:
            raise ValueError((f'{self.__class__.__name__}.remove(group): '
                              f'group {group} is not a member of this collection.'))

        if len(group):
            raise RuntimeError((f'{self.__class__.__name__}.remove(group): '
                                f'Group {group} is not empty.'))

        dispatch_event(PoseDrivenShapeKeyGroupDisposeEvent(group))
        self.collection__internal__.remove(index)
        self.active_index = min(len(self)-1, self.active_index)
        dispatch_event(PoseDrivenShapeKeyTargetRemovedEvent(self, index))
