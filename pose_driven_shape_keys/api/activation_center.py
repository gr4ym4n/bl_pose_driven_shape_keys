
from typing import Tuple, TYPE_CHECKING
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, FloatVectorProperty
from mathutils import Euler, Matrix, Quaternion, Vector
from ..lib.transform_utils import transform_matrix_flatten, transform_matrix_compose
from ..lib.events import dataclass, dispatch_event, Event
if TYPE_CHECKING:
    from bpy.types import Context


@dataclass(frozen=True)
class ActivationCenterUpdateEvent(Event):
    center: 'PoseDrivenShapeKeyActivationCenter'


def center_property_update_handler(center: 'PoseDrivenShapeKeyActivationCenter',
                                   _: 'Context') -> None:
    dispatch_event(ActivationCenterUpdateEvent(center))


def center_location(center: 'PoseDrivenShapeKeyActivationCenter') -> Vector:
    return center.transform_matrix.to_translation()


def center_location_set(center: 'PoseDrivenShapeKeyActivationCenter',
                        vector: Tuple[float, float, float]) -> None:
    matrix = transform_matrix_compose(vector,
                                      center_rotation_quaternion(center),
                                      center_scale(center))
    center.transform_matrix = transform_matrix_flatten(matrix)


def center_rotation_euler(center: 'PoseDrivenShapeKeyActivationCenter') -> Euler:
    return center.transform_matrix.to_euler()


def center_rotation_euler_set(center: 'PoseDrivenShapeKeyActivationCenter',
                              vector: Tuple[float, float, float]) -> None:
    center_rotation_quaternion_set(center, Euler(vector).to_quaternion())


def center_rotation_quaternion(center: 'PoseDrivenShapeKeyActivationCenter') -> 'Quaternion':
    return center.transform_matrix.to_quaternion()


def center_rotation_quaternion_set(center: 'PoseDrivenShapeKeyActivationCenter',
                               vector: Tuple[float, float, float, float]) -> None:
    matrix = transform_matrix_compose(center_location(center),
                                      vector,
                                      center_scale(center))
    center.transform_matrix = transform_matrix_flatten(matrix)


def center_scale(center: 'PoseDrivenShapeKeyActivationCenter') -> Vector:
    return center.transform_matrix.to_scale()


def center_scale_set(center: 'PoseDrivenShapeKeyActivationCenter',
                     vector: Tuple[float, float, float]) -> None:
        matrix = transform_matrix_compose(center_location(center),
                                          center_rotation_quaternion(center),
                                          vector)
        center.transform_matrix = transform_matrix_flatten(matrix)


class PoseDrivenShapeKeyActivationCenter(PropertyGroup):

    bbone_curveinx: FloatProperty(
        name="X",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_curveiny: FloatProperty(
        name="Y",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_curveinz: FloatProperty(
        name="Z",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_curveoutx: FloatProperty(
        name="X",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_curveouty: FloatProperty(
        name="Y",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_curveoutz: FloatProperty(
        name="Z",
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_easein: FloatProperty(
        name="In",
        min=-5.0,
        max=5.0,
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_easeout: FloatProperty(
        name="Out",
        min=-5.0,
        max=5.0,
        default=0.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_rollin: FloatProperty(
        name="In",
        default=0.0,
        precision=3,
        subtype='ANGLE',
        options=set(),
        update=center_property_update_handler
        )

    bbone_rollout: FloatProperty(
        name="Out",
        default=0.0,
        precision=3,
        subtype='ANGLE',
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleinx: FloatProperty(
        name="X",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleiny: FloatProperty(
        name="Y",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleinz: FloatProperty(
        name="Z",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleoutx: FloatProperty(
        name="X",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleouty: FloatProperty(
        name="Y",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    bbone_scaleoutz: FloatProperty(
        name="Z",
        default=1.0,
        precision=3,
        options=set(),
        update=center_property_update_handler
        )

    location: FloatVectorProperty(
        name="Location",
        size=3,
        subtype='XYZ',
        precision=3,
        get=center_location,
        set=center_location_set,
        options=set()
        )

    rotation_euler: FloatVectorProperty(
        name="Rotation",
        size=3,
        subtype='EULER',
        precision=3,
        get=center_rotation_euler,
        set=center_rotation_euler_set,
        options=set()
        )

    rotation_quaternion: FloatVectorProperty(
        name="Rotation",
        size=4,
        subtype='QUATERNION',
        precision=3,
        get=center_rotation_quaternion,
        set=center_rotation_quaternion_set,
        options=set()
        )

    scale: FloatVectorProperty(
        name="Scale",
        size=3,
        subtype='XYZ',
        precision=3,
        get=center_scale,
        set=center_scale_set,
        options=set()
        )

    transform_matrix: FloatVectorProperty(
        name="Transform Matrix",
        size=16,
        subtype='MATRIX',
        default=transform_matrix_flatten(Matrix.Identity(4)),
        update=center_property_update_handler,
        options=set()
        )


