
from typing import Sequence, TYPE_CHECKING
import numpy as np
from ..lib.events import event_handler
from ..api.activation_center import ActivationCenterUpdateEvent
from . import distance
if TYPE_CHECKING:
    from ..api.activation_center import PoseDrivenShapeKeyActivationCenter
    from ..api.activation import PoseDrivenShapeKeyActivation
    from ..api.shape_key import PoseDrivenShapeKey


def resolve_activation_center_shape_key(center: 'PoseDrivenShapeKeyActivationCenter') -> 'PoseDrivenShapeKey':
    path: str = center.path_from_id()
    return center.id_data.path_resolve(path.rpartition(".activation.")[0])


def pose_radii(distance_matrix: np.ndarray) -> Sequence[float]:
    radii = []
    for row in np.ma.masked_values(distance_matrix, 0.0, atol=0.001):
        row = row.compressed()
        radii.append(0.0 if len(row) == 0 else np.min(row))
    return radii


@event_handler(ActivationCenterUpdateEvent)
def on_activation_center_update(event: ActivationCenterUpdateEvent) -> None:
    shape = resolve_activation_center_shape_key(event.center)
    group = shape.group
    radii = pose_radii(distance.matrix(group))
    for shape, radius in zip(group, radii):
        activation: 'PoseDrivenShapeKeyActivation' = shape.activation
        if activation.radius_auto_update:
            activation.radius = radius
