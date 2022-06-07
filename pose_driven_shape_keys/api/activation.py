
from typing import TYPE_CHECKING
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, PointerProperty
from ..lib.curve_mapping import BCLMAP_CurveManager
from ..lib.events import dataclass, dispatch_event, Event
from .activation_center import PoseDrivenShapeKeyActivationCenter
if TYPE_CHECKING:
    from bpy.types import Context


@dataclass(frozen=True)
class ActivationRadiusUpdateEvent(Event):
    activation: 'PoseDrivenShapeKeyActivation'
    value: float


@dataclass(frozen=True)
class ActivationTargetUpdateEvent(Event):
    activation: 'PoseDrivenShapeKeyActivation'
    value: float


@dataclass(frozen=True)
class ActivationUpdateEvent(Event):
    activation: 'PoseDrivenShapeKeyActivation'


def activation_radius_update_handler(activation: 'PoseDrivenShapeKeyActivation',
                                     _: 'Context') -> None:
    dispatch_event(ActivationRadiusUpdateEvent(activation, activation.radius))


def activation_target_update_handler(activation: 'PoseDrivenShapeKeyActivation',
                                     _: 'Context') -> None:
    dispatch_event(ActivationTargetUpdateEvent(activation, activation.target))


class PoseDrivenShapeKeyActivation(BCLMAP_CurveManager, PropertyGroup):

    center: PointerProperty(
        name="Center",
        description="",
        type=PoseDrivenShapeKeyActivationCenter,
        options=set()
        )

    radius: FloatProperty(
        name="Radius",
        description=("The pose driver's radius. Controls how close to the center "
                     "the target's values are before the shape key is activated."),
        min=0.0,
        max=1.0,
        default=0.2,
        precision=3,
        update=activation_radius_update_handler,
        options=set()
        )

    radius_auto_update: BoolProperty(
        name="Auto-Update",
        description="Automatically adjust the radius to the nearest neighboring pose",
        default=True,
        options=set()
        )

    target: FloatProperty(
        name="Goal",
        description="The value of the shape key when fully activated",
        default=1.0,
        options=set(),
        update=activation_target_update_handler
        )

    def update(self) -> None:
        super().update()
        dispatch_event(ActivationUpdateEvent(self))
