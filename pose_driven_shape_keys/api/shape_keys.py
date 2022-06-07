
from typing import Iterator, List, Optional, Tuple, Union
from bpy.types import PropertyGroup, ShapeKey
from bpy.props import CollectionProperty,  PointerProperty
from ..lib.events import dataclass, dispatch_event, Event
from .group import PoseDrivenShapeKeyGroup
from .groups import PoseDrivenShapeKeyGroups
from .shape_key import PoseDrivenShapeKey


@dataclass(frozen=True)
class PoseDrivenShapeKeyCreatedEvent(Event):
    shapekey: PoseDrivenShapeKey


@dataclass(frozen=True)
class PoseDrivenShapeKeyDisposeEvent(Event):
    shapekey: PoseDrivenShapeKey


@dataclass(frozen=True)
class PoseDrivenShapeKeyRemovedEvent(Event):
    shapekeys: 'PoseDrivenShapeKeys'
    index: int


class PoseDrivenShapeKeys(PropertyGroup):

    collection__internal__: CollectionProperty(
        type=PoseDrivenShapeKey,
        options={'HIDDEN'}
        )

    groups: PointerProperty(
        name="Groups",
        description="Pose driven shape key groups",
        type=PoseDrivenShapeKeyGroups,
        options=set()
        )

    def __contains__(self, key: Union[PoseDrivenShapeKey, str]) -> bool:
        if isinstance(key, str):
            return self.find(key) != -1
        for item in self:
            if item == key:
                return True
        return False

    def __len__(self) -> int:
        return len(self.collection__internal__)

    def __iter__(self) -> Iterator[PoseDrivenShapeKey]:
        return iter(self.collection__internal__)

    def __getitem__(self, key: Union[str, int, slice]) -> Union[PoseDrivenShapeKey, List[PoseDrivenShapeKey]]:
        return self.collection__internal__[key]

    def find(self, key: str) -> int:
        return self.collection__internal__.find(key)

    def get(self, name: str, fallback: Optional[object]=None) -> Optional[PoseDrivenShapeKey]:
        return self.collection__internal__.get(name, fallback)

    def keys(self) -> Iterator[str]:
        return self.collection__internal__.keys()

    def items(self) -> Iterator[Tuple[str, PoseDrivenShapeKey]]:
        return self.collection__internal__.items()

    def values(self) -> Iterator[PoseDrivenShapeKey]:
        return self.collection__internal__.values()

    def new(self, shape: ShapeKey, group: Optional[PoseDrivenShapeKeyGroup]) -> PoseDrivenShapeKey:
        if not isinstance(shape, ShapeKey):
            raise TypeError((f'{self.__class__.__name__}.new(shape, target=None): '
                             f'Expected shape to be ShapeKey, not {shape.__class__.__name__}'))

        if group is None:
            group = self.targets.active or self.targets.new()
        else:
            if not isinstance(group, PoseDrivenShapeKeyGroup):
                raise TypeError((f'{self.__class__.__name__}.new(shape, target=None): '
                                 f'Expected target to be PoseDrivenShapeKeyGroup,'
                                 f' not {group.__class__.__name__}'))

            if self.targets.index(group) == -1:
                raise ValueError((f'{self.__class__.__name__}.new(shape, target=None): '
                                  f'target is not a target for this Key'))
        
        item = self.collection__internal__.add()
        item.__init__(shape, group)
        dispatch_event(PoseDrivenShapeKeyCreatedEvent(item))
        return item

    def remove(self, item: PoseDrivenShapeKey) -> None:
        if not isinstance(item, PoseDrivenShapeKey):
            raise TypeError((f'{self.__class__.__name__}.remove(item): '
                             f'Expected item to be PoseDrivenShapeKey, '
                             f'not {item.__class__.__name__}'))

        index = next((i for i, x in enumerate(self) if x == item), -1)
        if index == -1:
            raise ValueError((f'{self.__class__.__name__}.remove(item): '
                             f'item {item} is not a member of this collection.'))

        dispatch_event(PoseDrivenShapeKeyDisposeEvent(item))
        self.collection__internal__.remove(index)
        dispatch_event(PoseDrivenShapeKeyRemovedEvent(self, index))