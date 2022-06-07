
from ctypes import Union
from typing import Iterator, Optional, TYPE_CHECKING, Tuple
from bpy.types import Object, PropertyGroup
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty
from ..lib.events import dataclass, dispatch_event, Event
from ..lib.mixins import Identifiable
from .activation_center import PoseDrivenShapeKeyActivationCenter
if TYPE_CHECKING:
    from .shape_key import PoseDrivenShapeKey


@dataclass(frozen=True)
class GroupBoneTargetUpdateEvent(Event):
    group: 'PoseDrivenShapeKeyGroup'
    value: str
    previous_value: str


@dataclass(frozen=True)
class GroupNameUpdateEvent(Event):
    group: 'PoseDrivenShapeKeyGroup'
    value: str
    previous_value: str


@dataclass(frozen=True)
class GroupObjectUpdateEvent(Event):
    group: 'PoseDrivenShapeKeyGroup'
    value: Optional[Object]
    previous_value: Optional[Object]


@dataclass(frozen=True)
class GroupPropertyFlagUpdateEvent(Event):
    group: 'PoseDrivenShapeKeyGroup'
    name: str
    value: bool


def group_bone_target(target: 'PoseDrivenShapeKeyGroup') -> str:
    animdata = target.id_data.animation_data
    if animdata:
        driven = next(target.driven, None)
        if driven:
            datapath = f'["pdw_{driven.identifier}"]'
            for fcurve in animdata.drivers:
                if fcurve.data_path == datapath:
                    variables = fcurve.driver.variables
                    if len(variables) > 0:
                        variable = variables[0]
                        if variable.type == 'TRANSFORMS':
                            return variable.targets[0].bone_target
                        else:
                            datapath = variable.targets[0].data_path
                            if datapath.startswith('pose.bones["'):
                                return datapath[12:datapath.find('"]')]
                        break
    return target.get("bone_target", "")


def group_bone_group_set(group: 'PoseDrivenShapeKeyGroup', value: str) -> None:
    cache = group_bone_target(group)
    group["bone_target"] = value
    dispatch_event(GroupBoneTargetUpdateEvent(group, value, cache))


def group_name(group: 'PoseDrivenShapeKeyGroup') -> str:
    return group.get("name", "")


def group_name_set(group: 'PoseDrivenShapeKeyGroup', value: str) -> None:
    cache = group_name(group)
    names = group.id_data.pose_driven.targets.keys()
    index = 0
    basis = value
    while value in names:
        index += 1
        value = f'{basis}.{str(index).zfill(3)}'
    group['name'] = value
    dispatch_event(GroupNameUpdateEvent(group, value, cache))


def group_object_validate(_: 'PoseDrivenShapeKeyGroup', object: Object) -> bool:
    return object.type == 'ARMATURE'


class PoseDrivenShapeKeyGroup(Identifiable, PropertyGroup):

    def update(self) -> None:
        identifier = self.identifier
        for driven in self.id_data.pose_driven.shape_keys:
            if driven.target == identifier:
                driven.update()

    bone_target: StringProperty(
        name="Bone",
        description="The pose bone to read values from",
        get=group_bone_target,
        set=group_bone_group_set,
        options=set()
        )

    bbone_curveinx: BoolProperty(
        name="X",
        description="Use the target bendy-bone's curve-in X",
        default=False,
        options=set(),
        update=update
        )

    bbone_curveiny: BoolProperty(
        name="Y",
        description="Use the target bendy-bone's curve-in Y",
        default=False,
        options=set(),
        update=update
        )

    bbone_curveinz: BoolProperty(
        name="Z",
        description="Use the target bendy-bone's curve-in Z",
        default=False,
        options=set(),
        update=update
        )

    bbone_curveoutx: BoolProperty(
        name="X",
        description="Use the target bendy-bone's curve-out X",
        default=False,
        options=set(),
        update=update
        )

    bbone_curveouty: BoolProperty(
        name="Y",
        description="Use the target bendy-bone's curve-out Y",
        default=False,
        options=set(),
        update=update
        )

    bbone_curveoutz: BoolProperty(
        name="Z",
        description="Use the target bendy-bone's curve-out Z",
        default=False,
        options=set(),
        update=update
        )

    bbone_easein: BoolProperty(
        name="In",
        description="Use the target bendy-bone's ease-in",
        default=False,
        options=set(),
        update=update
        )

    bbone_easeout: BoolProperty(
        name="Out",
        description="Use the target bendy-bone's ease-out",
        default=False,
        options=set(),
        update=update
        )

    bbone_rollin: BoolProperty(
        name="In",
        description="Use the target bendy-bone's roll-in",
        default=False,
        options=set(),
        update=update
        )

    bbone_rollout: BoolProperty(
        name="Out",
        description="Use the target bendy-bone's roll-out",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleinx: BoolProperty(
        name="X",
        description="Use the target bendy-bone's scale-in X",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleiny: BoolProperty(
        name="Y",
        description="Use the target bendy-bone's scale-in Y",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleinz: BoolProperty(
        name="Z",
        description="Use the target bendy-bone's scale-in Z",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleoutx: BoolProperty(
        name="X",
        description="Use the target bendy-bone's scale-out X",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleouty: BoolProperty(
        name="Y",
        description="Use the target bendy-bone's scale-out Y",
        default=False,
        options=set(),
        update=update
        )

    bbone_scaleoutz: BoolProperty(
        name="Z",
        description="Use the target bendy-bone's scale-out Z",
        default=False,
        options=set(),
        update=update
        )

    @property
    def is_empty(self) -> bool:
        name = self.name
        for item in self.id_data.pose_driven:
            if item.get("group", "") == name:
                return False
        return True

    @property
    def is_enabled(self) -> bool:
        return (self.rotation
                or self.rotation_x
                or self.rotation_y
                or self.rotation_z
                or self.location_x
                or self.location_y
                or self.location_z
                or self.scale_x
                or self.scale_y
                or self.scale_z
                or self.bbone_curveinx
                or self.bbone_curveinz
                or self.bbone_curveoutx
                or self.bbone_curveoutz
                or self.bbone_rollin
                or self.bbone_rollout
                or self.bbone_easein
                or self.bbone_easeout
                or self.bbone_scaleinx
                or self.bbone_scaleiny
                or self.bbone_scaleinz
                or self.bbone_scaleoutx
                or self.bbone_scaleouty
                or self.bbone_scaleoutz)

    @property
    def is_valid(self) -> bool:
        object = self.object
        target = self.bone_target
        return object is not None and object.type == 'ARMATURE' and target in object.data.bones

    location_x: BoolProperty(
        name="X",
        description="Use the target bone's X location",
        default=False,
        options=set(),
        update=update
        )

    location_y: BoolProperty(
        name="Y",
        description="Use the target bone's Y location",
        default=False,
        options=set(),
        update=update
        )

    location_z: BoolProperty(
        name="Z",
        description="Use the target bone's Z location",
        default=False,
        options=set(),
        update=update
        )

    name: StringProperty(

        )

    object: PointerProperty(
        name="Object",
        description="The armature object",
        type=Object,
        poll=group_object_validate,
        update=update,
        options=set()
        )

    rest: PointerProperty(
        name="Rest",
        description="Rest pose",
        type=PoseDrivenShapeKeyActivationCenter,
        options=set()
        )

    rotation: BoolProperty(
        name="Rotation",
        description="Use the target bone's rotation",
        default=False,
        options=set(),
        update=update
        )

    rotation_axis: EnumProperty(
        name="Axis",
        description="The rotation axis to use",
        items=[
            ('X', "X", "X-axis"),
            ('Y', "Y", "Y-axis"),
            ('Z', "Z", "Z-axis"),
            ],
        default='Y',
        options=set(),
        update=update
        )

    rotation_mode: EnumProperty(
        name="Mode",
        description="Rotation Mode",
        items=[
            ('EULER'     , "Euler"     , "Euler angles"       ),
            ('QUATERNION', "Quaternion", "Quaternion rotation"),
            ('SWING'     , "Swing"     , "Swing rotation"     ),
            ('TWIST'     , "Twist"     , "Twist rotation"     ),
            ],
        default='',
        options=set(),
        update=update
        )

    rotation_order: EnumProperty(
        name="Order",
        description="Euler rotation order",
        items=[
            ('AUTO', "Auto", "Euler using the rotation order of the target"),
            ('XYZ' , "XYZ" , "Euler using the XYZ rotation order"),
            ('XZY' , "XZY" , "Euler using the XZY rotation order"),
            ('YXZ' , "YXZ" , "Euler using the YXZ rotation order"),
            ('YZX' , "YZX" , "Euler using the YZX rotation order"),
            ('ZXY' , "ZXY" , "Euler using the ZXY rotation order"),
            ('ZYX' , "ZYX" , "Euler using the ZYX rotation order"),
            ],
        default='AUTO',
        options=set(),
        update=update
        )

    rotation_x: BoolProperty(
        name="X",
        description="Use the target bone's X rotation",
        default=False,
        options=set(),
        update=update
        )

    rotation_y: BoolProperty(
        name="Y",
        description="Use the target bone's Y rotation",
        default=False,
        options=set(),
        update=update
        )

    rotation_z: BoolProperty(
        name="Z",
        description="Use the target bone's Z rotation",
        default=False,
        options=set(),
        update=update
        )

    scale_x: BoolProperty(
        name="X",
        description="Use the target bone's X scale",
        default=False,
        options=set(),
        update=update
        )

    scale_y: BoolProperty(
        name="Y",
        description="Use the target bone's Y scale",
        default=False,
        options=set(),
        update=update
        )

    scale_z: BoolProperty(
        name="Z",
        description="Use the target bone's Z scale",
        default=False,
        options=set(),
        update=update
        )

    def __init__(self, name: str) -> None:
        self["name"] = name

    def __contains__(self, key: Union['PoseDrivenShapeKey', str]) -> bool:
        if isinstance(key, str):
            for item in self:
                if item.name == key:
                    return True
            return False
        for item in self:
            if item == key:
                return True
        return False

    def __len__(self) -> int:
        return len(list(self))

    def __iter__(self) -> Iterator['PoseDrivenShapeKey']:
        name = self.name
        for item in self.id_data.pose_driven:
            if item.get("group", "") == name:
                yield item


def group_flags_location(group: PoseDrivenShapeKeyGroup) -> Tuple[bool, bool, bool]:
    return (group.location_x, group.location_y, group.location_z)


def group_flags_rotation(group: PoseDrivenShapeKeyGroup) -> Tuple[bool, bool, bool]:
    return (group.rotation_x, group.rotation_y, group.rotation_z)


def group_flags_scale(group: PoseDrivenShapeKeyGroup) -> Tuple[bool, bool, bool]:
    return (group.scale_x, group.scale_y, group.scale_z)


def group_flags_bbone(group: PoseDrivenShapeKeyGroup) -> Tuple[bool, ...]:
    return (group.bbone_curveinx,
            group.bbone_curveinz,
            group.bbone_curveoutx,
            group.bbone_curveoutx,
            group.bbone_easein,
            group.bbone_easeout,
            group.bbone_rollin,
            group.bbone_rollout,
            group.bbone_scaleinx,
            group.bbone_scaleiny,
            group.bbone_scaleinz,
            group.bbone_scaleoutx,
            group.bbone_scaleouty,
            group.bbone_scaleoutz,)