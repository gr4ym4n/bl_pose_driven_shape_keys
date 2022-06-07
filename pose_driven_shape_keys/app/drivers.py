
from typing import TYPE_CHECKING
from ..lib.events import event_handler
from ..api.group import (GroupBoneTargetUpdateEvent,
                         GroupObjectUpdateEvent,
                         GroupPropertyFlagUpdateEvent)
if TYPE_CHECKING:
    from bpy.types import Driver
    from ..api.shape_key import PoseDrivenShapeKey




def driver_update(driver: 'Driver', driven: 'PoseDrivenShapeKey') -> None:
    pass


@event_handler(GroupBoneTargetUpdateEvent)
def on_group_bone_target_update(event: GroupBoneTargetUpdateEvent) -> None:
    pass


@event_handler(GroupObjectUpdateEvent)
def on_group_object_update(event: GroupObjectUpdateEvent) -> None:
    pass


@event_handler(GroupPropertyFlagUpdateEvent)
def on_group_property_flag_update(event: GroupPropertyFlagUpdateEvent) -> None:
    pass

