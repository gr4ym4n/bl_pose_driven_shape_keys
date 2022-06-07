
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bpy.types import ID
    from ..lib.mixins import Identifiable
    from ..api.shape_key import PoseDrivenShapeKey

PREFIX = "pds"


def ensure(owner: 'Identifiable', suffix: str) -> str:
    name = f'{PREFIX}_{suffix}_{owner.identifier}'
    owner.id_data[name] = 0.0
    return f'["{name}"]'


def ensure_location(driven: 'PoseDrivenShapeKey') -> str:
    return ensure(driven, "loc")


def ensure_rotation(driven: 'PoseDrivenShapeKey') -> str:
    return ensure(driven, "rot")


def ensure_scale(driven: 'PoseDrivenShapeKey') -> str:
    return ensure(driven, "sca")


def ensure_bbone(driven: 'PoseDrivenShapeKey') -> str:
    return ensure(driven, 'bbn')