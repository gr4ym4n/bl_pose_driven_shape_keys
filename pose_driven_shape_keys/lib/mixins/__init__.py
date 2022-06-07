
from uuid import uuid4
from bpy.types import PropertyGroup
from bpy.props import StringProperty


def identifier(identifiable: 'Identifiable') -> str:
    value = PropertyGroup.get(identifiable, "identifier")
    if not value:
        value = uuid4().hex
        PropertyGroup.__setitem__(identifiable, "identifier", value)
    return value


class Identifiable:

    identifier: StringProperty(
        name="Identifier",
        description="Unique data identifier (read-only)",
        get=identifier,
        options={'HIDDEN'}
        )