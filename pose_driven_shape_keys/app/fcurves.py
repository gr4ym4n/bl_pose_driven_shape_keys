
from typing import TYPE_CHECKING, Union
from ..lib.events import event_handler
from ..lib.curve_mapping import to_bezier, keyframe_points_assign
from ..api.activation import ActivationRadiusUpdateEvent, ActivationTargetUpdateEvent
from ..api.shape_key import ShapeKeyMuteUpdateEvent
from . import resolve
if TYPE_CHECKING:
    from bpy.types import FCurve
    from ..api.activation import PoseDrivenShapeKeyActivation


def fcurve_update(fcurve: 'FCurve', activation: PoseDrivenShapeKeyActivation) -> None:
    radius = activation.radius
    target = activation.target
    rangex = (1.0-radius, 1.0)
    rangey = (0.0, target)
    points = activation.points
    points = to_bezier(points, x_range=rangex, y_range=rangey, extrapolate=False)
    keyframe_points_assign(fcurve.keyframe_points, points)


def on_activation_fcurve_update(event: Union[ActivationRadiusUpdateEvent, ActivationTargetUpdateEvent]) -> None:
    activation = event.activation
    fcurve = resolve.driven_value_driver(resolve.activation_shape(activation))
    fcurve_update(fcurve, activation)


@event_handler(ActivationRadiusUpdateEvent)
def on_activation_radius_update(event: ActivationRadiusUpdateEvent) -> None:
    on_activation_fcurve_update(event)


@event_handler(ActivationTargetUpdateEvent)
def on_activation_target_update(event: ActivationTargetUpdateEvent) -> None:
    on_activation_fcurve_update(event)


@event_handler(ShapeKeyMuteUpdateEvent)
def on_shape_key_mute_update(event: ShapeKeyMuteUpdateEvent) -> None:
    fcurve = resolve.driven_value_driver(event.shapekey)
    fcurve.mute = event.value
