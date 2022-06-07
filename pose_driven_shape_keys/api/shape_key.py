
from typing import TYPE_CHECKING
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, PointerProperty
from ..lib.mixins import Identifiable
from ..lib.events import dataclass, dispatch_event, Event
from .activation import PoseDrivenShapeKeyActivation
if TYPE_CHECKING:
    from bpy.types import Context, ShapeKey
    from .group import PoseDrivenShapeKeyGroup


@dataclass(frozen=True)
class ShapeKeyMuteUpdateEvent(Event):
    shapekey: 'PoseDrivenShapeKey'
    value: bool


def shapekey_mute_update_handler(shape: 'PoseDrivenShapeKey', _: 'Context') -> None:
    dispatch_event(ShapeKeyMuteUpdateEvent(shape, shape.mute))


class PoseDrivenShapeKey(Identifiable, PropertyGroup):

    activation: PointerProperty(
        name="Activation",
        description="Activation settings",
        type=PoseDrivenShapeKeyActivation,
        options=set()
        )

    mute: BoolProperty(
        name="Mute",
        description=("Whether or not the driven shape key's driver is enabled. Disabling "
                     "the driver allows (temporary) editing of the shape key's value in the UI"),
        default=False,
        options=set(),
        update=shapekey_mute_update_handler
        )

    @property
    def group(self) -> 'PoseDrivenShapeKeyGroup':
        return self.id_data.pose_driven.groups.get(self.get("group", ""))

    def __init__(self, shape: 'ShapeKey', group: 'PoseDrivenShapeKeyGroup') -> None:
        self["name"] = shape.name
        self["group"] = group.name
