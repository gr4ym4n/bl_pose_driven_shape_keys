
from typing import TYPE_CHECKING
from ..lib.driver_utils import driver_ensure
if TYPE_CHECKING:
    from bpy.types import FCurve
    from ..api.activation import PoseDrivenShapeKeyActivation
    from ..api.shape_key import PoseDrivenShapeKey


def activation_shape(activation: 'PoseDrivenShapeKeyActivation') -> 'PoseDrivenShapeKey':
    path: str = activation.path_from_id()
    return activation.id_data.path_resolve(path.rpartition(".activation")[0])


def driven_value_driver(driven: 'PoseDrivenShapeKey') -> FCurve:
    return driver_ensure(driven.id_data, f'key_blocks["{driven.name}"].value')
