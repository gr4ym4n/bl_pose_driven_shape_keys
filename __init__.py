# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Pose-Driven Shape Keys",
    "description": "Pose-driven corrective shape keys.",
    "author": "James Snowden",
    "version": (1, 0, 0),
    "blender": (2, 90, 0),
    "location": "View3D",
    "warning": "",
    "doc_url": "https://pose_driven_shape_keys.github.io",
    "tracker_url": "https://github.com/jamesvsnowden/bl_pose_driven_shape_keys/issues",
    "category": "Animation",
}

import math
import typing
import uuid
import bpy
import mathutils
from .lib import curve_mapping
from .lib.driver_utils import DriverVariableNameGenerator, driver_ensure, driver_find, driver_remove, driver_variables_clear
from .lib.curve_mapping import BCLMAP_CurveManager, to_bezier, keyframe_points_assign, draw_curve_manager_ui
from .lib.transform_utils import transform_matrix, transform_matrix_compose, transform_matrix_flatten
from .lib.symmetry import symmetrical_target

curve_mapping.BLCMAP_OT_curve_copy.bl_idname = "pose_driver_shape_keys.curve_copy"
curve_mapping.BLCMAP_OT_curve_paste.bl_idname = "pose_driver_shape_keys.curve_paste"
curve_mapping.BLCMAP_OT_curve_edit.bl_idname = "pose_driver_shape_keys.curve_edit"

COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'}
COMPAT_OBJECTS = {'MESH', 'LATTICE', 'CURVE', 'SURFACE'}

def bbone_values_apply(props: 'PoseDrivenShapeKey', bone: bpy.types.PoseBone, set_flags: typing.Optional[bool]=False) -> None:
    v3 = bpy.app.version[0] >= 3
    v2 = not v3
    props["bbone_curveinx"]      = bone.bbone_curveinx
    props["bbone_curveiny"]      = bone.bbone_curveiny if v2 else 0.0
    props["bbone_curveinz"]      = bone.bbone_curveinz if v3 else 0.0
    props["bbone_curveoutx"]     = bone.bbone_curveoutx
    props["bbone_curveouty"]     = bone.bbone_curveouty if v2 else 0.0
    props["bbone_curveoutz"]     = bone.bbone_curveoutz if v3 else 0.0
    props["bbone_easein"]        = bone.bbone_easein
    props["bbone_easeout"]       = bone.bbone_easeout
    props["bbone_rollin"]        = bone.bbone_rollin
    props["bbone_rollout"]       = bone.bbone_rollout
    props["bbone_scaleinx"]      = bone.bbone_scalein[0] if v3 else bone.bbone_scaleinx
    props["bbone_scaleiny"]      = bone.bbone_scalein[1] if v3 else bone.bbone_scaleiny
    props["bbone_scaleinz"]      = bone.bbone_scalein[2] if v3 else 0.0
    props["bbone_scaleoutx"]     = bone.bbone_scaleout[0] if v3 else bone.bbone_scaleoutx
    props["bbone_scaleouty"]     = bone.bbone_scaleout[1] if v3 else bone.bbone_scaleouty
    props["bbone_scaleoutz"]     = bone.bbone_scaleout[2] if v3 else 0.0
    if set_flags:
        props["use_bbone_curveinx"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveinx, 0.0, abs_tol=0.001)
        props["use_bbone_curveiny"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveiny, 0.0, abs_tol=0.001) if v2 else False
        props["use_bbone_curveinz"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveinz, 0.0, abs_tol=0.001) if v3 else False
        props["use_bbone_curveoutx"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveoutx, 0.0, abs_tol=0.001)
        props["use_bbone_curveouty"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveouty, 0.0, abs_tol=0.001) if v2 else False
        props["use_bbone_curveoutz"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_curveoutz, 0.0, abs_tol=0.001) if v3 else False
        props["use_bbone_easein"]    = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_easein, 0.0, asb_tol=0.001)
        props["use_bbone_easeout"]   = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_easeout, 0.0, asb_tol=0.001)
        props["use_bbone_rollin"]    = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_rollin, 0.0, asb_tol=0.001)
        props["use_bbone_rollout"]   = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_rollout, 0.0, asb_tol=0.001)
        props["use_bbone_scaleinx"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scalein[0] if v3 else bone.bbone_scaleinx, 1.0, abs_tol=0.001)
        props["use_bbone_scaleiny"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scalein[1] if v3 else bone.bbone_scaleiny, 1.0, abs_tol=0.001)
        props["use_bbone_scaleinz"]  = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scalein[2] if v3 else 1.0, 1.0, abs_tol=0.001)
        props["use_bbone_scaleoutx"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scaleout[0] if v3 else bone.bbone_scaleoutx, 1.0, abs_tol=0.001)
        props["use_bbone_scaleouty"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scaleout[1] if v3 else bone.bbone_scaleouty, 1.0, abs_tol=0.001)
        props["use_bbone_scaleoutz"] = bone.bone.bbone_segments > 1 and not math.isclose(bone.bbone_scaleout[2] if v3 else 1.0, 1.0, abs_tol=0.001)

def xform_values_apply(props: 'PoseDrivenShapeKey', bone: bpy.props.PoseBone, set_flags: typing.Optional[bool]=False) -> None:
    matrix = transform_matrix(bone, 'LOCAL_SPACE')
    props["transform_matrix"] = transform_matrix_flatten(matrix)
    if set_flags:
        for prop, vector, default in zip(("location", "scale"),
                                        (matrix.to_translation(), matrix.to_scale()),
                                        (0.0, 1.0)):
            for axis, value in zip('xyz', vector):
                props[f'use_{prop}_{axis}'] = not math.isclose(value, default, abs_tol=0.001)
        mode = props.rotation_mode
        if mode == 'QUATERNION':
            props["use_rotation"] = any(not math.isclose(a, b, abs_tol=0.001) for a, b in (matrix.to_quaternion(), (1.0, 0.0, 0.0, 0.0)))
        elif mode == 'TWIST':
            props["use_rotation"] = not math.isclose(matrix.to_quaternion().to_swing_twist('Y')[1], 0.0, abs_tol=0.001)
        elif mode == 'SWING':
            props["use_rotation"] = not math.isclose(matrix.to_quaternion().to_swing_twist('Y')[0][0], 1.0, abs_tol=0.001)
        else:
            for axis, value in zip("xyz", matrix.to_euler()):
                props[f'use_rotation_{axis}'] = not math.isclose(value, 0.0, abs_tol=0.001)

def distance_fcurve_set(points: bpy.types.FCurveKeyframePoints, distance: float) -> None:
    while len(points) > 2:
        points.remove(points[-2])

    for point, (co, hl, hr) in zip(points, (
        ((0., 1.), (-.25, 1.), (distance*.25, .75)),
        ((distance, 0.), (distance*.75, .25), (distance*1.25, 0.))
        )):
        point.interpolation = 'BEZIER'
        point.co = co
        point.handle_left_type = 'FREE'
        point.handle_right_type = 'FREE'
        point.handle_left = hl
        point.handle_right = hr

class PoseDrivenShapeKeyCurveMap(curve_mapping.BCLMAP_CurveManager, bpy.types.PropertyGroup):

    def update(self, context: typing.Optional[bpy.types.Context] = None) -> None:
        super().update(context)
        self.id_data.path_resolve(self.path_from_id().rpartition(".")[0]).update()

class PoseDrivenShapeKey(bpy.types.PropertyGroup):
    """Manages and stores settings for a pose driven shape key"""

    def get_bone_target(self) -> str:
        animdata = self.id_data.animation_data
        if animdata:
            datapath = f'["{self.identifier}_distances"]'
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
        return ""

    def get_location(self) -> mathutils.Vector:
        return self.transform_matrix.to_translation()

    def set_location(self, value: typing.Tuple[float, float, float]) -> None:
        matrix = transform_matrix_compose(value, self.get_rotation_quaternion(), self.get_scale())
        self.transform_matrix = transform_matrix_flatten(matrix)

    def get_rotation_quaternion(self) -> mathutils.Quaternion:
        return self.transform_matrix.to_quaternion()

    def set_rotation_quaternion(self, value: typing.Tuple[float, float, float, float]) -> None:
        matrix = transform_matrix_compose(self.get_location(), value, self.get_scale())
        self.transform_matrix = transform_matrix_flatten(matrix)

    def get_rotation_euler(self) -> mathutils.Euler:
        return self.transform_matrix.to_euler()

    def set_rotation_euler(self, value: typing.Tuple[float, float, float]) -> None:
        self.set_rotation_quaternion(mathutils.Euler(value).to_quaternion())

    def get_rotation_swing(self) -> mathutils.Vector:
        swing = self.get_rotation_quaternion().to_swing_twist('Y')[0]
        sin_s = math.sqrt(pow(swing[1], 2)+pow(swing[3], 2))
        if sin_s > 0.0:
            cos_s = swing[0]
            if sin_s < cos_s:
                scale = 2.0 * math.asin(min(max(-1.0, sin_s), 1.0)) / sin_s
            else:
                scale = 2.0 * math.acos(min(max(-1.0, cos_s), 1.0)) / sin_s
            return mathutils.Vector((swing[1] * scale, swing[3] * scale))
        else:
            return mathutils.Vector((0.0, 0.0))

    def set_rotation_swing(self, value: typing.Tuple[float, float]) -> None:
        # TODO
        pass

# +void swing_twist_to_quat(float quat[4],
# +                         const float swing_twist[3],
# +                         const int twist_axis)
# +{
# +  /* Assemble the twist quaternion. */
# +  const float t = swing_twist[twist_axis] * 0.5f;
# +  float twist[4];
# +  twist[0] = cosf(t);
# +  zero_v3(twist + 1);
# +  twist[twist_axis + 1] = sinf(t);
# +
# +  const int *const idx = swing_idx_table[twist_axis];
# +  const float s = sqrtf(pow2f(swing_twist[idx[0]]) + pow2f(swing_twist[idx[1]]));
# +  if (s > 0.0f) {
# +    /* Assemble the swing quaternion. */
# +    const float sa = 0.5f * s;
# +    const float sin_s = sinf(sa);
# +    const float scale = sin_s / s;
# +    float swing[4];
# +    swing[0] = cosf(sa);
# +    swing[idx[0] + 1] = swing_twist[idx[0]] * scale;
# +    swing[idx[1] + 1] = swing_twist[idx[1]] * scale;
# +    swing[twist_axis + 1] = 0.0f;
# +
# +    /* Multiply swing and twist quaternions to get final quaternion. */
# +    mul_qt_qtqt(quat, swing, twist);
# +  }
# +  else {
# +    copy_v4_v4(quat, twist);
# +  }
# +}

    def get_rotation_twist(self) -> float:
        return self.get_rotation_quaternion().to_swing_twist('Y')[1]

    def set_rotation_twist(self, value: float) -> None:
        swing, _ = self.get_rotation_quaternion().to_swing_twist('Y')
        twist = mathutils.Quaternion((math.cos(value*0.5), 0.0, -math.sin(value*0.5), 0.0))
        self.set_rotation_quaternion(swing @ twist.inverted())

    def get_scale(self) -> mathutils.Vector:
        return self.transform_matrix.to_scale()

    def set_scale(self, value: typing.Tuple[float, float, float]) -> None:
        matrix = transform_matrix_compose(self.get_location(), self.get_rotation_quaternion(), value)
        self.transform_matrix = transform_matrix_flatten(matrix)

    def update(self, context: typing.Optional[typing.Union[bpy.types.Context, str]]=None) -> None:

        if isinstance(context, str):
            bone_target = context
            prev_target = self.get_bone_target()
            if bone_target and not prev_target:
                object = self.object
                if object is not None and object.type == 'ARMATURE':
                    bone = object.pose.bones.get(bone_target)
                    if bone is not None:
                        xform_values_apply(self, bone, set_flags=True)
                        bbone_values_apply(self, bone, set_flags=True)
        else:
            bone_target = self.get_bone_target()

        key = self.id_data
        distance_data_prop = f'{self.identifier}_distances'
        distance_data_path = f'["{distance_data_prop}"]'
        distance_data = []
        matrix = self.transform_matrix

        animdata = key.animation_data
        if animdata:
            for fcurve in tuple(animdata.drivers):
                if fcurve.data_path == distance_data_path:
                    animdata.drivers.remove(fcurve)
        
        flags = (self.use_location_x, self.use_location_y, self.use_location_z)
        if True in flags:
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
            driver = fcurve.driver
            points = fcurve.keyframe_points
            tokens = []
            values = matrix.to_translation()

            driver_variables_clear(driver.variables)

            for axis, flag, value in zip('XYZ', flags, values):
                if flag:
                    variable = driver.variables.new()
                    variable.type = 'TRANSFORMS'
                    variable.name = axis.lower()

                    target = variable.targets[0]
                    target.id = self.object
                    target.bone_target = bone_target
                    target.transform_type = f'LOC_{axis}'
                    target.transform_space = 'LOCAL_SPACE'

                    tokens.append((variable.name, str(value)))

            driver.type = 'SCRIPTED'
            driver.expression = f'sqrt({"+".join("pow("+a+"-"+b+",2.0)" for a, b in tokens)})'

            distance = math.sqrt(sum([pow(value, 2) for value in values]))
            distance_fcurve_set(points, distance)

        mode = self.rotation_mode

        if mode == 'QUATERNION' and self.use_rotation:
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
            driver = fcurve.driver
            points = fcurve.keyframe_points
            tokens = []
            values = matrix.to_quaternion()

            driver_variables_clear(driver.variables)

            for axis, value in zip('WXYZ', values):
                variable = driver.variables.new()
                variable.type = 'TRANSFORMS'
                variable.name = axis.lower()

                target = variable.targets[0]
                target.id = self.object
                target.bone_target = bone_target
                target.rotation_mode = 'QUATERNION'
                target.transform_type = f'ROT_{axis}'
                target.transform_space = 'LOCAL_SPACE'

                tokens.append((variable.name, str(value)))

            driver.type = 'SCRIPTED'
            driver.expression = f'acos((2.0*pow(clamp({"+".join(a+"*"+b for a, b in tokens)},-1.0,1.0),2.0))-1.0)/pi'

            identity = (1.0, 0.0, 0.0, 0.0)
            distance = math.acos((2.0*pow(min(max(-1.0, sum([a*b for a, b in zip(values, identity)])), 1.0), 2.0))-1.0)/math.pi
            distance_fcurve_set(points, distance)

        elif mode == 'TWIST' and self.use_rotation:
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
            driver = fcurve.driver
            points = fcurve.keyframe_points
            value = matrix.to_quaternion().to_swing_twist('Y')[1]

            driver_variables_clear(driver.variables)

            variable = driver.variables.new()
            variable.type = 'TRANSFORMS'
            variable.name = axis.lower()

            target = variable.targets[0]
            target.id = self.object
            target.bone_target = bone_target
            target.rotation_mode = 'SWING_TWIST_Y'
            target.transform_type = 'ROT_Y'
            target.transform_space = 'LOCAL_SPACE'

            driver.type = 'SCRIPTED'
            driver.expression = f'fabs({variable.name}-{str(value)})/pi'

            distance = value/math.pi
            distance_fcurve_set(points, distance)

        elif mode == 'SWING' and self.use_rotation:
            
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
            driver = fcurve.driver
            points = fcurve.keyframe_points
            tokens = []
            values = matrix.to_quaternion()

            driver_variables_clear(driver.variables)

            for axis in 'WXYZ':
                variable = driver.variables.new()
                variable.type = 'TRANSFORMS'
                variable.name = axis.lower()

                target = variable.targets[0]
                target.id = self.object
                target.bone_target = bone_target
                target.rotation_mode = 'QUATERNION'
                target.transform_type = f'ROT_{axis}'
                target.transform_space = 'LOCAL_SPACE'

            w, x, y, z = matrix.to_quaternion()
            a = str(2.0*(x*y-w*z))
            b = str(1.0-2.0*(x*x+z*z))
            c = str(2.0*(y*z+w*x))

            driver.type = 'SCRIPTED'
            driver.expression = f'(asin(2.0*(x*y-w*z)*{a}+(1.0-2.0*(x*x+z*z))*{b}+2.0*(y*z+w*x)*{c})--(pi/2.0))/pi'
            distance_fcurve_set(points, 1.0)

        else:
            flags = (self.use_rotation_x, self.use_rotation_y, self.use_rotation_z)
            if True in flags:
                distance_data.append(0.0)

                fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
                driver = fcurve.driver
                points = fcurve.keyframe_points
                tokens = []
                values = matrix.to_euler()

                driver_variables_clear(driver.variables)

                for axis, flag, value in zip('XYZ', flags, values):
                    if flag:
                        variable = driver.variables.new()
                        variable.type = 'TRANSFORMS'
                        variable.name = axis.lower()

                        target = variable.targets[0]
                        target.id = self.object
                        target.bone_target = bone_target
                        target.rotation_mode = mode
                        target.transform_type = f'ROT_{axis}'
                        target.transform_space = 'LOCAL_SPACE'

                        tokens.append((variable.name, str(value)))

                driver.type = 'SCRIPTED'
                driver.expression = f'sqrt({"+".join("pow("+a+"-"+b+",2.0)" for a, b in tokens)})'

                distance = math.sqrt(sum([pow(value, 2) for value in values]))
                distance_fcurve_set(points, distance)

        flags = (self.use_scale_x, self.use_scale_y, self.use_scale_z)
        if True in flags:
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, len(distance_data)-1)
            driver = fcurve.driver
            points = fcurve.keyframe_points
            tokens = []
            values = matrix.to_scale()

            driver_variables_clear(driver.variables)

            for axis, flag, value in zip('XYZ', flags, values):
                if flag:
                    variable = driver.variables.new()
                    variable.type = 'TRANSFORMS'
                    variable.name = axis.lower()

                    target = variable.targets[0]
                    target.id = self.object
                    target.bone_target = bone_target
                    target.transform_type = f'SCALE_{axis}'
                    target.transform_space = 'LOCAL_SPACE'

                    tokens.append((variable.name, str(value)))

            driver.type = 'SCRIPTED'
            driver.expression = f'sqrt({"+".join("pow("+a+"-"+b+",2.0)" for a, b in tokens)})'

            distance = math.sqrt(sum([pow(value, 2) for value in values]))
            distance_fcurve_set(points, distance)

        fcurve = None
        driver = None
        keygen = None
        tokens = []
        values = []

        for prop in ("bbone_curveinx",
                     "bbone_curveiny",
                     "bbone_curveinz",
                     "bbone_curveoutx",
                     "bbone_curveouty",
                     "bbone_curveoutz",
                     "bbone_easein",
                     "bbone_easeout",
                     "bbone_rollin",
                     "bbone_rollout",
                     "bbone_scaleinx",
                     "bbone_scaleiny",
                     "bbone_scaleinz",
                     "bbone_scaleoutx",
                     "bbone_scaleouty",
                     "bbone_scaleoutz"):
            if getattr(self, f'use_{prop}'):
                if driver is None:
                    fcurve = driver_ensure(key, distance_data_path, len(distance_data))
                    driver = fcurve.driver
                    keygen = DriverVariableNameGenerator()
                    driver_variables_clear(driver.variables)
                    distance_data.append(0.0)
                
                variable = driver.variables.new()
                variable.name = next(keygen)
                variable.type = 'SINGLE_PROP'

                target = variable.targets[0]
                target.id = self.object
                target.data_path = f'pose.bones["{bone_target}"].{prop}'

                tokens.append((variable.name, getattr(self, prop), float("scale" in prop)))

        if driver:
            driver.type = 'SCRIPTED'
            driver.expression = f'sqrt({"+".join("pow("+a+"-"+str(b)+",2.0)" for a, b, _ in tokens)})'

            distance = math.sqrt(sum([pow(b-c, 2) for _, b, c in tokens]))
            distance_fcurve_set(points, distance)

        if not distance_data:
            # Fake driver used to track bone target name
            distance_data.append(0.0)

            fcurve = driver_ensure(key, distance_data_path, 0)
            driver = fcurve.driver
            driver.type = 'SCRIPTED'
            driver.expression = "0.0"
            driver_variables_clear(driver.variables)

            variable = driver.variables.new()
            variable.name = "var"
            variable.type = 'TRANSFORMS'

            target = variable.targets[0]
            target.id = self.object
            target.bone_target = bone_target

        key[distance_data_prop] = distance_data

        fcurve = driver_ensure(key, self.data_path)
        driver = fcurve.driver
        driver.type = 'AVERAGE'
        driver_variables_clear(driver.variables)

        variable = driver.variables.new()
        variable.type = 'SINGLE_PROP'
        variable.name = f'posedriver_{self.identifier}'

        target = variable.targets[0]
        target.id_type = 'KEY'
        target.id = key
        target.data_path = 'reference_key.value'

        for index in range(len(distance_data)):
            variable = driver.variables.new()
            variable.type = 'SINGLE_PROP'
            variable.name = f'distance_{len(driver.variables)}'

            target = variable.targets[0]
            target.id_type = 'KEY'
            target.id = key
            target.data_path = f'{distance_data_path}[{index}]'

        points = to_bezier(self.falloff.curve.points,
                           x_range=(1.0-self.radius, 1.0),
                           y_range=(0.0, self.value),
                           extrapolate=False)

        keyframe_points_assign(fcurve.keyframe_points, points)

    bbone_curveinx: bpy.props.FloatProperty(
        name="X",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_curveiny: bpy.props.FloatProperty(
        name="Y",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_curveinz: bpy.props.FloatProperty(
        name="Z",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_curveoutx: bpy.props.FloatProperty(
        name="X",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_curveouty: bpy.props.FloatProperty(
        name="Y",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_curveoutz: bpy.props.FloatProperty(
        name="Z",
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_easein: bpy.props.FloatProperty(
        name="In",
        min=-5.0,
        max=5.0,
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_easeout: bpy.props.FloatProperty(
        name="Out",
        min=-5.0,
        max=5.0,
        default=0.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_rollin: bpy.props.FloatProperty(
        name="In",
        default=0.0,
        precision=3,
        subtype='ANGLE',
        options=set(),
        update=update
        )

    bbone_rollout: bpy.props.FloatProperty(
        name="Out",
        default=0.0,
        precision=3,
        subtype='ANGLE',
        options=set(),
        update=update
        )

    bbone_scaleinx: bpy.props.FloatProperty(
        name="X",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_scaleiny: bpy.props.FloatProperty(
        name="Y",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_scaleinz: bpy.props.FloatProperty(
        name="Z",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_scaleoutx: bpy.props.FloatProperty(
        name="X",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_scaleouty: bpy.props.FloatProperty(
        name="Y",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bbone_scaleoutz: bpy.props.FloatProperty(
        name="Z",
        default=1.0,
        precision=3,
        options=set(),
        update=update
        )

    bone_target: bpy.props.StringProperty(
        name="Bone",
        description="The bone to read rotations from",
        get=get_bone_target,
        set=update,
        options=set()
        )

    @property
    def data_path(self) -> str:
        return f'key_blocks["{self.name}"].value'

    falloff: bpy.props.PointerProperty(
        name="Falloff",
        description="The falloff curve for the driver",
        type=PoseDrivenShapeKeyCurveMap,
        options=set()
        )

    identifier: bpy.props.StringProperty(
        name="Shape",
        description="Unique identifier used to hold a reference to the driven shape key.",
        get=lambda self: self.get("identifier", ""),
        options={'HIDDEN'}
        )

    location: bpy.props.FloatVectorProperty(
        name="Location",
        size=3,
        subtype='XYZ',
        precision=3,
        get=get_location,
        set=set_location,
        options=set()
        )

    mute: bpy.props.BoolProperty(
        name="Mute",
        description=("Whether or not the driven shape key's driver is enabled. Disabling "
                     "the driver allows (temporary) editing of the shape key's value in the UI"),
        default=False,
        options=set(),
        update=update
        )

    object: bpy.props.PointerProperty(
        name="Object",
        description="The armature object",
        type=bpy.types.Object,
        poll=lambda _, ob: ob.type == 'ARMATURE',
        update=update,
        options=set()
        )

    transform_matrix: bpy.props.FloatVectorProperty(
        name="Transform Matrix",
        size=16,
        subtype='MATRIX',
        default=transform_matrix_flatten(mathutils.Matrix.Identity(4)),
        update=update,
        options=set()
        )

    radius: bpy.props.FloatProperty(
        name="Radius",
        description=("The pose driver's radius. Controls how close to the center "
                     "the target's values are before the shape key is activated."),
        min=0.0,
        max=1.0,
        default=0.2,
        precision=3,
        update=update,
        options=set()
        )

    rotation_euler: bpy.props.FloatVectorProperty(
        name="Rotation",
        size=3,
        subtype='EULER',
        precision=3,
        get=get_rotation_euler,
        set=set_rotation_euler,
        options=set()
        )

    rotation_mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('AUTO'      , "Auto Euler", "Euler using the rotation order of the target", 'NONE', 0),
            ('XYZ'       , "XYZ Euler" , "Euler using the XYZ rotation order"          , 'NONE', 1),
            ('XZY'       , "XZY Euler" , "Euler using the XZY rotation order"          , 'NONE', 2),
            ('YXZ'       , "YXZ Euler" , "Euler using the YXZ rotation order"          , 'NONE', 3),
            ('YZX'       , "YZX Euler" , "Euler using the YZX rotation order"          , 'NONE', 4),
            ('ZXY'       , "ZXY Euler" , "Euler using the ZXY rotation order"          , 'NONE', 5),
            ('ZYX'       , "ZYX Euler" , "Euler using the ZYX rotation order"          , 'NONE', 6),
            ('QUATERNION', "Quaternion", "Quaternion rotation"                         , 'NONE', 7),
            ('SWING'     , "Swing"     , "Swing rotation to aim the Y axis"            , 'NONE', 8),
            ('TWIST'     , "Twist"     , "Twist rotation around the Y axis"            , 'NONE', 9),
            ],
        default='QUATERNION',
        update=update,
        options=set()
        )

    rotation_swing: bpy.props.FloatVectorProperty(
        name="Rotation",
        size=2,
        unit='ROTATION',
        precision=3,
        get=get_rotation_swing,
        set=set_rotation_swing,
        options=set()
        )

    rotation_twist: bpy.props.FloatProperty(
        name="Rotation",
        subtype='ANGLE',
        precision=3,
        get=get_rotation_twist,
        set=set_rotation_twist,
        options=set()
        )

    rotation_quaternion: bpy.props.FloatVectorProperty(
        name="Rotation",
        size=4,
        subtype='QUATERNION',
        precision=3,
        get=get_rotation_quaternion,
        set=set_rotation_quaternion,
        options=set()
        )

    scale: bpy.props.FloatVectorProperty(
        name="Scale",
        size=3,
        subtype='XYZ',
        precision=3,
        get=get_scale,
        set=set_scale,
        options=set()
        )

    value: bpy.props.FloatProperty(
        name="Goal",
        description="The value of the shape key when fully activated by the driver",
        default=1.0,
        options=set(),
        update=update
        )

    use_bbone_curveinx: bpy.props.BoolProperty(
        name="X",
        description="Use the target bendy-bone's curve-in X",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_curveiny: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bendy-bone's curve-in Y",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_curveinz: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bendy-bone's curve-in Z",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_curveoutx: bpy.props.BoolProperty(
        name="X",
        description="Use the target bendy-bone's curve-out X",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_curveouty: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bendy-bone's curve-out Y",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_curveoutz: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bendy-bone's curve-out Z",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_easein: bpy.props.BoolProperty(
        name="In",
        description="Use the target bendy-bone's ease-in",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_easeout: bpy.props.BoolProperty(
        name="Out",
        description="Use the target bendy-bone's ease-out",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_rollin: bpy.props.BoolProperty(
        name="In",
        description="Use the target bendy-bone's roll-in",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_rollout: bpy.props.BoolProperty(
        name="Out",
        description="Use the target bendy-bone's roll-out",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleinx: bpy.props.BoolProperty(
        name="X",
        description="Use the target bendy-bone's scale-in X",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleiny: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bendy-bone's scale-in Y",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleinz: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bendy-bone's scale-in Z",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleoutx: bpy.props.BoolProperty(
        name="X",
        description="Use the target bendy-bone's scale-out X",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleouty: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bendy-bone's scale-out Y",
        default=False,
        options=set(),
        update=update
        )

    use_bbone_scaleoutz: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bendy-bone's scale-out Z",
        default=False,
        options=set(),
        update=update
        )

    use_location_x: bpy.props.BoolProperty(
        name="X",
        description="Use the target bone's X location",
        default=False,
        options=set(),
        update=update
        )

    use_location_y: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bone's Y location",
        default=False,
        options=set(),
        update=update
        )

    use_location_z: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bone's Z location",
        default=False,
        options=set(),
        update=update
        )

    use_rotation: bpy.props.BoolProperty(
        name="Rotation",
        description="Use the target bone's rotation",
        default=False,
        options=set(),
        update=update
        )

    use_rotation_x: bpy.props.BoolProperty(
        name="X",
        description="Use the target bone's X rotation",
        default=False,
        options=set(),
        update=update
        )

    use_rotation_y: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bone's Y rotation",
        default=False,
        options=set(),
        update=update
        )

    use_rotation_z: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bone's Z rotation",
        default=False,
        options=set(),
        update=update
        )

    use_scale_x: bpy.props.BoolProperty(
        name="X",
        description="Use the target bone's X scale",
        default=False,
        options=set(),
        update=update
        )

    use_scale_y: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bone's Y scale",
        default=False,
        options=set(),
        update=update
        )

    use_scale_z: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bone's Z scale",
        default=False,
        options=set(),
        update=update
        )

    use_scale_x: bpy.props.BoolProperty(
        name="X",
        description="Use the target bone's X scale",
        default=False,
        options=set(),
        update=update
        )

    use_scale_y: bpy.props.BoolProperty(
        name="Y",
        description="Use the target bone's Y scale",
        default=False,
        options=set(),
        update=update
        )

    use_scale_z: bpy.props.BoolProperty(
        name="Z",
        description="Use the target bone's Z scale",
        default=False,
        options=set(),
        update=update
        )

# region Operators
###################################################################################################

class SHAPEKEYPOSEDRIVER_OT_add(bpy.types.Operator):

    bl_idname = 'shape_key_pose_driver.add'
    bl_label = "Add Pose Driver"
    bl_description = "Add a pose driver to the shape key"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.engine in COMPAT_ENGINES:
            object = context.object
            if object is not None and object.type in COMPAT_OBJECTS:
                shape = object.active_shape_key
                if shape is not None:
                    key = shape.id_data
                    return (key.use_relative
                            and shape != key.reference_key
                            and (not key.is_property_set("pose_drivers")
                                 or shape.name not in key.pose_drivers))
        return False

    def execute(self, context: bpy.types.Context) -> typing.Set[str]:
        object = context.object
        shape = object.active_shape_key
        key = shape.id_data
        settings = key.pose_drivers.add()
        settings["name"] = shape.name
        settings["identifier"] = f'posedriver_{uuid.uuid4()}'
        settings["value"] = shape.value if shape.value > 0.01 else 1.0
        settings.falloff.__init__(interpolation='QUAD', easing='EASE_IN_OUT')
        settings.update()
        return {'FINISHED'}

COPY_PASTE_BUFFER = None

class SHAPEKEYPOSEDRIVER_OT_copy(bpy.types.Operator):

    bl_idname = 'shape_key_pose_driver.copy'
    bl_label = "Copy Pose Driver"
    bl_description = "Copy the shape key's pose driver"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.engine in COMPAT_ENGINES:
            object = context.object
            if object is not None and object.type in COMPAT_OBJECTS:
                shape = object.active_shape_key
                if shape is not None:
                    key = shape.id_data
                    return (key.use_relative
                            and shape != key.reference_key
                            and key.is_property_set("pose_drivers")
                            and shape.name in key.pose_drivers)
        return False

    def execute(self, context: bpy.types.Context) -> typing.Set[str]:
        object = context.object
        shape = object.active_shape_key
        key = shape.id_data
        settings = key.pose_drivers[shape.name]
        global COPY_PASTE_BUFFER
        COPY_PASTE_BUFFER = {
            "object": settings.object.name if settings.object else "",
            "bone_target": symmetrical_target(settings.bone_target) or settings.bone_target,
            "transform_matrix": settings.transform_matrix.copy(),
            "bbone_curveinx": settings.bbone_curveinx,
            "bbone_curveiny": settings.bbone_curveiny,
            "bbone_curveinz": settings.bbone_curveinz,
            "bbone_curveoutx": settings.bbone_curveoutx,
            "bbone_curveouty": settings.bbone_curveouty,
            "bbone_curveoutz": settings.bbone_curveoutz,
            "bbone_easein": settings.bbone_easein,
            "bbone_easeout": settings.bbone_easeout,
            "bbone_rollin": settings.bbone_rollin,
            "bbone_rollout": settings.bbone_rollout,
            "bbone_scaleinx": settings.bbone_scaleinx,
            "bbone_scaleiny": settings.bbone_scaleiny,
            "bbone_scaleinz": settings.bbone_scaleinz,
            "bbone_scaleoutx": settings.bbone_scaleoutx,
            "bbone_scaleouty": settings.bbone_scaleouty,
            "bbone_scaleoutz": settings.bbone_scaleoutz,
            "mute": settings.mute,
            "radius": settings.radius,
            "rotation_mode": settings.get("rotation_mode", 7),
            "show_pose_values": settings.show_pose_values,
            "value": settings.value,
            "use_bbone_curveinx": settings.use_bbone_curveinx,
            "use_bbone_curveiny": settings.use_bbone_curveiny,
            "use_bbone_curveinz": settings.use_bbone_curveinz,
            "use_bbone_curveoutx": settings.use_bbone_curveoutx,
            "use_bbone_curveouty": settings.use_bbone_curveouty,
            "use_bbone_curveoutz": settings.use_bbone_curveoutz,
            "use_bbone_easein": settings.use_bbone_easein,
            "use_bbone_easeout": settings.use_bbone_easeout,
            "use_bbone_rollin": settings.use_bbone_rollin,
            "use_bbone_rollout": settings.use_bbone_rollout,
            "use_bbone_scaleinx": settings.use_bbone_scaleinx,
            "use_bbone_scaleiny": settings.use_bbone_scaleiny,
            "use_bbone_scaleinz": settings.use_bbone_scaleinz,
            "use_bbone_scaleoutx": settings.use_bbone_scaleoutx,
            "use_bbone_scaleouty": settings.use_bbone_scaleouty,
            "use_bbone_scaleoutz": settings.use_bbone_scaleoutz,
            "use_location_x": settings.use_location_x,
            "use_location_y": settings.use_location_y,
            "use_location_z": settings.use_location_z,
            "use_rotation": settings.use_rotation,
            "use_rotation_x": settings.use_rotation_x,
            "use_rotation_y": settings.use_rotation_y,
            "use_rotation_z": settings.use_rotation_z,
            "use_scale_x": settings.use_scale_x,
            "use_scale_y": settings.use_scale_y,
            "use_scale_z": settings.use_scale_z,
            "use_scale_x": settings.use_scale_x,
            "use_scale_y": settings.use_scale_y,
            "use_scale_z": settings.use_scale_z,
            "falloff": {
                "curve_type": settings.falloff.get("curve_type", 0),
                "interpolation": settings.falloff.get("interpolation", 0),
                "easing": settings.falloff.get("easing", 2),
                "ramp": settings.falloff.get("ramp", 2),
                "curve": {
                    "extend": settings.falloff.curve.get("extend", 0),
                    "points": [{
                        "location": tuple(point.location),
                        "handle_type": point.get("handle_type", 0),
                        "select": point.select
                    } for point in settings.falloff.curve.points]
                    }
                }
            }
        return {'FINISHED'}

class SHAPEKEYPOSEDRIVER_OT_paste(bpy.types.Operator):

    bl_idname = 'shape_key_pose_driver.paste'
    bl_label = "Paste Pose Driver"
    bl_description = "Paste the copied pose driver to the shape key"
    bl_options = {'INTERNAL', 'UNDO'}

    mirror: bpy.props.BoolProperty(
        name="Mirror",
        default=False,
        options=set()
        )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.engine in COMPAT_ENGINES:
            object = context.object
            if object is not None and object.type in COMPAT_OBJECTS:
                shape = object.active_shape_key
                if shape is not None:
                    key = shape.id_data
                    return (key.use_relative
                            and shape != key.reference_key
                            and bool(COPY_PASTE_BUFFER))
        return False

    def execute(self, context: bpy.types.Context) -> typing.Set[str]:
        object = context.object
        shape = object.active_shape_key
        key = shape.id_data
        buffer = COPY_PASTE_BUFFER
        settings = key.pose_drivers.get(shape.name)
        
        if settings is None:
            settings = key.pose_drivers.add()
            settings["name"] = shape.name
            settings["identifier"] = f'posedriver_{uuid.uuid4()}'
            settings.falloff.__init__(interpolation='QUAD', easing='EASE_IN_OUT')

        settings["object"] = context.blend_data.objects.get(buffer.get("object", ""), None)
        settings["bone_target"] = buffer.get("bone_target", "")

        # matrix = buffer.get("transform_matrix", transform_matrix_flatten(mathutils.Matrix.Identity(4)))
        # if self.mirror:
        #     matrix = mathutils.Matrix(matrix[0:4], matrix[4:8], matrix[8:12], matrix[12:16])
        #     matrix = transform_matrix_flatten(matrix @ mathutils.Matrix(((-1., 0., 0., 0.),
        #                                                                  (0. , 1., 0., 0.),
        #                                                                  (0. , 0., 1., 0.),
        #                                                                  (0. , 0., 0., 1.))))

        # TODO decompose and mirror
        settings["transform_matrix"] = transform_matrix_flatten(buffer["transform_matrix"])

        # TODO mirror bbone properties

        settings["bbone_curveinx"] = buffer["bbone_curveinx"]
        settings["bbone_curveiny"] = buffer["bbone_curveiny"]
        settings["bbone_curveinz"] = buffer["bbone_curveinz"]
        settings["bbone_curveoutx"] = buffer["bbone_curveoutx"]
        settings["bbone_curveouty"] = buffer["bbone_curveouty"]
        settings["bbone_curveoutz"] = buffer["bbone_curveoutz"]
        settings["bbone_easein"] = buffer["bbone_easein"]
        settings["bbone_easeout"] = buffer["bbone_easeout"]
        settings["bbone_rollin"] = buffer["bbone_rollin"]
        settings["bbone_rollout"] = buffer["bbone_rollout"]
        settings["bbone_scaleinx"] = buffer["bbone_scaleinx"]
        settings["bbone_scaleiny"] = buffer["bbone_scaleiny"]
        settings["bbone_scaleinz"] = buffer["bbone_scaleinz"]
        settings["bbone_scaleoutx"] = buffer["bbone_scaleoutx"]
        settings["bbone_scaleouty"] = buffer["bbone_scaleouty"]
        settings["bbone_scaleoutz"] = buffer["bbone_scaleoutz"]
        settings["mute"] = buffer["mute"]
        settings["radius"] = buffer["radius"]
        settings["rotation_mode"] = buffer["rotation_mode"]
        settings["show_pose_values"] = buffer["show_pose_values"]
        settings["value"] = buffer["value"]
        settings["use_bbone_curveinx"] = buffer["use_bbone_curveinx"]
        settings["use_bbone_curveiny"] = buffer["use_bbone_curveiny"]
        settings["use_bbone_curveinz"] = buffer["use_bbone_curveinz"]
        settings["use_bbone_curveoutx"] = buffer["use_bbone_curveoutx"]
        settings["use_bbone_curveouty"] = buffer["use_bbone_curveouty"]
        settings["use_bbone_curveoutz"] = buffer["use_bbone_curveoutz"]
        settings["use_bbone_easein"] = buffer["use_bbone_easein"]
        settings["use_bbone_easeout"] = buffer["use_bbone_easeout"]
        settings["use_bbone_rollin"] = buffer["use_bbone_rollin"]
        settings["use_bbone_rollout"] = buffer["use_bbone_rollout"]
        settings["use_bbone_scaleinx"] = buffer["use_bbone_scaleinx"]
        settings["use_bbone_scaleiny"] = buffer["use_bbone_scaleiny"]
        settings["use_bbone_scaleinz"] = buffer["use_bbone_scaleinz"]
        settings["use_bbone_scaleoutx"] = buffer["use_bbone_scaleoutx"]
        settings["use_bbone_scaleouty"] = buffer["use_bbone_scaleouty"]
        settings["use_bbone_scaleoutz"] = buffer["use_bbone_scaleoutz"]
        settings["use_location_x"] = buffer["use_location_x"]
        settings["use_location_y"] = buffer["use_location_y"]
        settings["use_location_z"] = buffer["use_location_z"]
        settings["use_rotation"] = buffer["use_rotation"]
        settings["use_rotation_x"] = buffer["use_rotation_x"]
        settings["use_rotation_y"] = buffer["use_rotation_y"]
        settings["use_rotation_z"] = buffer["use_rotation_z"]
        settings["use_scale_x"] = buffer["use_scale_x"]
        settings["use_scale_y"] = buffer["use_scale_y"]
        settings["use_scale_z"] = buffer["use_scale_z"]
        settings["use_scale_x"] = buffer["use_scale_x"]
        settings["use_scale_y"] = buffer["use_scale_y"]
        settings["use_scale_z"] = buffer["use_scale_z"]

        src = buffer["falloff"]
        tgt = settings.falloff


        tgt["curve_type"] = src["curve_type"]
        tgt["interpolation"] = src["interpolation"]
        tgt["easing"] = src["easing"]
        tgt["ramp"] = src["ramp"]

        src = src["curve"]
        tgt = tgt.curve

        tgt["extend"] = src["extend"]

        points = tgt.points.points__internal__
        points.clear()
        for item in src["points"]:
            data = points.add()
            data["handle_type"] = item["handle_type"]
            data["location"] = item["location"]
            data["select"] = item["select"]

        BCLMAP_CurveManager.update(settings.falloff)

        settings.update()
        return {'FINISHED'}

class SHAPEKEYPOSEDRIVER_OT_remove(bpy.types.Operator):

    bl_idname = 'shape_key_pose_driver.remove'
    bl_label = "Remove Pose Driver"
    bl_description = "Remove the shape key's pose driver"
    bl_options = {'INTERNAL', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.engine in COMPAT_ENGINES:
            object = context.object
            if object is not None and object.type in COMPAT_OBJECTS:
                shape = object.active_shape_key
                if shape is not None:
                    key = shape.id_data
                    return (key.use_relative
                            and shape != key.reference_key
                            and key.is_property_set("pose_drivers")
                            and shape.name in key.pose_drivers)
        return False

    def execute(self, context: bpy.types.Context) -> typing.Set[str]:
        object = context.object
        shape = object.active_shape_key
        key = shape.id_data
        settings = key.pose_drivers[shape.name]

        animdata = key.animation_data
        if animdata:
            datapath = f'["{settings.identifier}_distances"]'
            for fcurve in list(animdata.drivers):
                if fcurve.data_path == datapath:
                    animdata.drivers.remove(fcurve)
        
        try:
            del key[f'{settings.identifier}_distances']
        except KeyError: pass

        driver_remove(key, f'key_blocks["{shape.name}"].value')
        key.pose_drivers.remove(key.pose_drivers.find(shape.name))
        return {'FINISHED'}

class SHAPEKEYPOSEDRIVER_OT_center_update(bpy.types.Operator):

    bl_idname = 'shape_key_pose_driver.center_update'
    bl_label = "Update Center"
    bl_description = "Update the pose values from the target's current pose"
    bl_options = {'INTERNAL', 'UNDO'}

    set_flags: bpy.props.BoolProperty(
        default=False,
        options=set()
        )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        if context.engine in COMPAT_ENGINES:
            object = context.object
            if object is not None and object.type in COMPAT_OBJECTS:
                shape = object.active_shape_key
                if shape is not None:
                    key = shape.id_data
                    if (key.use_relative
                        and shape != key.reference_key
                        and key.is_property_set("pose_drivers")):
                        settings = key.pose_drivers.get(shape.name)
                        if settings:
                            object = settings.object
                            return (object is not None
                                    and object.type == 'ARMATURE'
                                    and settings.bone_target in object.pose.bones)
        return False

    def execute(self, context: bpy.types.Context) -> typing.Set[str]:
        shape = context.object.active_shape_key
        settings = shape.id_data.pose_drivers[shape.name]
        object = settings.object
        bone = object.pose.bones[settings.bone_target]
        xform_values_apply(settings, bone, self.set_flags)
        bbone_values_apply(settings, bone, self.set_flags)
        settings.update()
        return {'FINISHED'}

#endregion Operators

def layout_split(layout: bpy.types.UILayout,
                 label: typing.Optional[str]="",
                 align: typing.Optional[bool]=False,
                 factor: typing.Optional[float]=0.385,
                 decorate: typing.Optional[bool]=True,
                 decorate_fill: typing.Optional[bool]=True
                 ) -> typing.Union[bpy.types.UILayout, typing.Tuple[bpy.types.UILayout, ...]]:
    split = layout.row().split(factor=factor)
    col_a = split.column(align=align)
    col_a.alignment = 'RIGHT'
    if label:
        col_a.label(text=label)
    row = split.row()
    col_b = row.column(align=align)
    if decorate:
        col_c = row.column(align=align)
        if decorate_fill:
            col_c.label(icon='BLANK1')
        else:
            return (col_b, col_c) if label else (col_a, col_b, col_c)
    return col_b if label else (col_a, col_b)

class SHAPEKEYPOSEDRIVER_MT_actions(bpy.types.Menu):
    bl_label = "Pose Driver Actions"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator(SHAPEKEYPOSEDRIVER_OT_center_update.bl_idname,
                        text="Read Pose Values",
                        icon='IMPORT').set_flags=False
        layout.operator(SHAPEKEYPOSEDRIVER_OT_center_update.bl_idname,
                        text="Read Pose Values (Auto-Keyed)",
                        icon='IMPORT').set_flags=True
        layout.separator()
        layout.operator(SHAPEKEYPOSEDRIVER_OT_copy.bl_idname,
                        icon='COPYDOWN',
                        text="Copy Pose Driver")
        layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                        icon='PASTEDOWN',
                        text="Paste Pose Driver").mirror=False
        layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                        icon='PASTEDOWN',
                        text="Paste Pose Driver (Mirrored)").mirror=True

class SHAPEKEYPOSEDRIVER_PT_settings(bpy.types.Panel):

    bl_parent_id = "DATA_PT_shape_keys"
    bl_label = "Pose Driver"
    bl_description = "Pose-driven shape key settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        object = context.object
        if object is not None:
            shape = object.active_shape_key
            if shape is not None:
                key = shape.id_data
                return (key.is_property_set("pose_drivers")
                        and shape.name in key.pose_drivers)
        return False

    def draw(self, context: bpy.types.Context) -> None:
        object = context.object
        target = object.active_shape_key
        layout = self.layout
        key = target.id_data
        settings = key.pose_drivers[target.name]
        
        values, decorations = layout_split(layout, "Target", align=True, decorate_fill=False)
        object = settings.object

        subrow = values.row(align=True)
        subrow.alert = object is None or object.type != 'ARMATURE'

        values.prop(settings, "object", text="")
        subrow = values.row(align=True)
        if object is None or object.type != 'ARMATURE':
            subrow.prop(settings, "bone_target", icon='BONE_DATA', text="")
        else:
            subrow.alert = settings.bone_target != "" and settings.bone_target not in object.data.bones
            subrow.prop_search(settings, "bone_target", object.data, "bones", icon='BONE_DATA', text="")

        decorations.menu("SHAPEKEYPOSEDRIVER_MT_actions", text="", icon='DOWNARROW_HLT')

        layout.separator()

        labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
        labels.label(text="Location X")
        labels.label(text="Y")
        labels.label(text="Z")

        row = values.row()
        row.enabled = settings.use_location_x
        row.prop(settings, "location", text="", index=0)

        row = values.row()
        row.enabled = settings.use_location_y
        row.prop(settings, "location", text="", index=1)

        row = values.row()
        row.enabled = settings.use_location_z
        row.prop(settings, "location", text="", index=2)

        decorations.prop(settings, "use_location_x", text="")
        decorations.prop(settings, "use_location_y", text="")
        decorations.prop(settings, "use_location_z", text="")

        mode = settings.rotation_mode

        labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
        labels.label(text="Rotation")
        values.prop(settings, "rotation_mode", text="")
        if len(mode) < 5:
            decorations.label(icon='BLANK1')
        else:
            decorations.prop(settings, "use_rotation", text="")

        if mode == 'QUATERNION':
            labels, values = layout_split(layout, align=True)
            labels.label(text="W")
            labels.label(text="X")
            labels.label(text="Y")
            labels.label(text="Z")
            values.enabled = settings.use_rotation
            values.prop(settings, "rotation_quaternion", text="", index=0)
            values.prop(settings, "rotation_quaternion", text="", index=1)
            values.prop(settings, "rotation_quaternion", text="", index=2)
            values.prop(settings, "rotation_quaternion", text="", index=3)

        elif mode == 'SWING':
            labels, values = layout_split(layout, align=True)
            labels.label(text="X")
            labels.label(text="Z")
            values.enabled = settings.use_rotation
            values.prop(settings, "rotation_swing", text="", index=0)
            values.prop(settings, "rotation_swing", text="", index=1)

        elif mode == 'TWIST':
            labels, values = layout_split(layout, align=True)
            labels.label(text="Y")
            values.enabled = settings.use_rotation
            values.prop(settings, "rotation_twist", text="")

        else:
            labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
            labels.label(text="X")
            labels.label(text="Y")
            labels.label(text="Z")

            row = values.row()
            row.enabled = settings.use_rotation_x
            row.prop(settings, "rotation_euler", text="", index=0)

            row = values.row()
            row.enabled = settings.use_rotation_y
            row.prop(settings, "rotation_euler", text="", index=1)

            row = values.row()
            row.enabled = settings.use_rotation_z
            row.prop(settings, "rotation_euler", text="", index=2)

            decorations.prop(settings, "use_rotation_x", text="")
            decorations.prop(settings, "use_rotation_y", text="")
            decorations.prop(settings, "use_rotation_z", text="")

        labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
        labels.label(text="Scale X")
        labels.label(text="Y")
        labels.label(text="Z")

        row = values.row()
        row.enabled = settings.use_scale_x
        row.prop(settings, "scale", text="", index=0)

        row = values.row()
        row.enabled = settings.use_scale_y
        row.prop(settings, "scale", text="", index=1)

        row = values.row()
        row.enabled = settings.use_scale_z
        row.prop(settings, "scale", text="", index=2)

        decorations.prop(settings, "use_scale_x", text="")
        decorations.prop(settings, "use_scale_y", text="")
        decorations.prop(settings, "use_scale_z", text="")

        layout.separator(factor=0.5)

        object = settings.object
        if object is not None and object.type == 'ARMATURE':
            bone = object.data.bones.get(settings.bone_target)

            if bone is not None and bone.bbone_segments > 1:

                v3 = bpy.app.version[0] >= 3

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
                labels.label(text="Curve In X")
                labels.label(text=f'{"Z" if v3 else "Y"}')

                row = values.row()
                row.enabled = settings.use_bbone_curveinx
                row.prop(settings, "bbone_curveinx", text="")

                row = values.row()
                row.enabled = getattr(settings, f'use_bbone_curvein{"z" if v3 else "y"}')
                row.prop(settings, f'bbone_curvein{"z" if v3 else "y"}', text="")

                decorations.prop(settings, "use_bbone_curveinx", text="")
                decorations.prop(settings, f'use_bbone_curvein{"z" if v3 else "y"}', text="")

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
                labels.label(text="Curve Out X")
                labels.label(text=f'{"Z" if v3 else "Y"}')

                row = values.row()
                row.enabled = settings.use_bbone_curveoutx
                row.prop(settings, "bbone_curveoutx", text="")

                row = values.row()
                row.enabled = getattr(settings, f'use_bbone_curveout{"z" if v3 else "y"}')
                row.prop(settings, f'bbone_curveout{"z" if v3 else "y"}', text="")

                decorations.prop(settings, "use_bbone_curveoutx", text="")
                decorations.prop(settings, f'use_bbone_curveout{"z" if v3 else "y"}', text="")

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)
                labels.label(text="Roll In")
                labels.label(text="Out")

                row = values.row()
                row.enabled = settings.use_bbone_rollin
                row.prop(settings, "bbone_rollin", text="")

                row = values.row()
                row.enabled = settings.use_bbone_rollout
                row.prop(settings, "bbone_rollout", text="")

                decorations.prop(settings, "use_bbone_rollin", text="")
                decorations.prop(settings, "use_bbone_rollout", text="")

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)

                labels.label(text="Scale In X")
                row = values.row()
                row.enabled = settings.use_bbone_scaleinx
                row.prop(settings, "bbone_scaleinx", text="")
                decorations.prop(settings, "use_bbone_scaleinx", text="")

                labels.label(text="Y")
                row = values.row()
                row.enabled = settings.use_bbone_scaleiny
                row.prop(settings, "bbone_scaleiny", text="")
                decorations.prop(settings, "use_bbone_scaleiny", text="")

                if v3:
                    labels.label(text="Z")
                    row = values.row()
                    row.enabled = settings.use_bbone_scaleinz
                    row.prop(settings, "bbone_scaleinz", text="")
                    decorations.prop(settings, "use_bbone_scaleinz", text="")

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)

                labels.label(text="Scale Out X")
                row = values.row()
                row.enabled = settings.use_bbone_scaleoutx
                row.prop(settings, "bbone_scaleoutx", text="")
                decorations.prop(settings, "use_bbone_scaleoutx", text="")

                labels.label(text="Y")
                row = values.row()
                row.enabled = settings.use_bbone_scaleouty
                row.prop(settings, "bbone_scaleouty", text="")
                decorations.prop(settings, "use_bbone_scaleouty", text="")

                if v3:
                    labels.label(text="Z")
                    row = values.row()
                    row.enabled = settings.use_bbone_scaleoutz
                    row.prop(settings, "bbone_scaleoutz", text="")
                    decorations.prop(settings, "use_bbone_scaleoutz", text="")

                labels, values, decorations = layout_split(layout, align=True, decorate_fill=False)

                labels.label(text="Ease In")
                row = values.row()
                row.enabled = settings.use_bbone_easein
                row.prop(settings, "bbone_easein", text="")
                decorations.prop(settings, "use_bbone_easein", text="")

                labels.label(text="Out")
                row = values.row()
                row.enabled = settings.use_bbone_easeout
                row.prop(settings, "bbone_easeout", text="")
                decorations.prop(settings, "use_bbone_easeout", text="")

                layout.separator()

        values = layout_split(layout, "Radius")
        values.prop(settings, "radius", text="")

        labels, values = layout_split(layout, decorate=False)
        labels.label(text="Easing")
        draw_curve_manager_ui(values, settings.falloff)
        layout_split(layout, label="Goal").prop(settings, "value", text="")

CLASSES = [
    curve_mapping.BLCMAP_CurvePointProperties,
    curve_mapping.BLCMAP_CurveProperties,
    curve_mapping.BLCMAP_CurvePoint,
    curve_mapping.BLCMAP_CurvePoints,
    curve_mapping.BLCMAP_Curve,
    curve_mapping.BLCMAP_OT_curve_copy,
    curve_mapping.BLCMAP_OT_curve_paste,
    curve_mapping.BLCMAP_OT_curve_edit,
    PoseDrivenShapeKeyCurveMap,
    PoseDrivenShapeKey,
    SHAPEKEYPOSEDRIVER_OT_add,
    SHAPEKEYPOSEDRIVER_OT_remove,
    SHAPEKEYPOSEDRIVER_OT_copy,
    SHAPEKEYPOSEDRIVER_OT_paste,
    SHAPEKEYPOSEDRIVER_OT_center_update,
    SHAPEKEYPOSEDRIVER_MT_actions,
    SHAPEKEYPOSEDRIVER_PT_settings,
    ]

def draw_menu_items(menu: bpy.types.Menu, context: bpy.types.Context) -> None:
    object = context.object
    if object is not None:
        shape = object.active_shape_key
        if shape is not None:
            key = shape.id_data
            if shape != key.reference_key:
                fcurve = driver_find(key, f'key_blocks["{shape.name}"].value')
                layout = None
                if fcurve is None:
                    layout = menu.layout
                    layout.separator()
                    layout.operator(SHAPEKEYPOSEDRIVER_OT_add.bl_idname,
                                    icon='DECORATE_DRIVER',
                                    text="Add Pose Driver")
                    layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                                    icon='PASTEDOWN',
                                    text="Paste Pose Driver").mirror=False
                    layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                                    icon='PASTEDOWN',
                                    text="Paste Pose Driver (Mirrored)").mirror=True
                else:
                    variables = fcurve.driver.variables
                    if len(variables) >= 1 and variables[0].name.startswith("posedriver_"):
                        layout = menu.layout
                        layout.separator()
                        layout.operator(SHAPEKEYPOSEDRIVER_OT_copy.bl_idname,
                                        icon='COPYDOWN',
                                        text="Copy Pose Driver")
                        layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                                        icon='PASTEDOWN',
                                        text="Paste Pose Driver").mirror=False
                        layout.operator(SHAPEKEYPOSEDRIVER_OT_paste.bl_idname,
                                        icon='PASTEDOWN',
                                        text="Paste Pose Driver (Mirrored)").mirror=True
                        layout.operator(SHAPEKEYPOSEDRIVER_OT_remove.bl_idname,
                                        icon='X',
                                        text="Remove Pose Driver")

MESSAGE_BROKER = object()

def shape_key_name_callback():
    for key in bpy.data.shape_keys:
        if key.is_property_set("pose_drivers"):
            animdata = key.animation_data
            if animdata:
                data = key.cone_based_drivers
                for fc in animdata.drivers:
                    vars = fc.driver.variables
                    if len(vars) == 2:
                        k = vars[0].name
                        if k.startswith("posedriver_") and k in data:
                            data[k]["name"] = fc.data_path[12:-8]

@bpy.app.handlers.persistent
def enable_message_broker(_=None) -> None:
    bpy.msgbus.clear_by_owner(MESSAGE_BROKER)
    bpy.msgbus.subscribe_rna(key=(bpy.types.ShapeKey, "name"),
                             owner=MESSAGE_BROKER,
                             args=tuple(),
                             notify=shape_key_name_callback)

class register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Key.pose_drivers = bpy.props.CollectionProperty(
        name="Pose Driven Corrective Shape Keys",
        type=PoseDrivenShapeKey,
        options=set()
        )

    bpy.types.MESH_MT_shape_key_context_menu.append(draw_menu_items)
    bpy.app.handlers.load_post.append(enable_message_broker)
    enable_message_broker() # Ensure messages are subscribed to on first install

def unregister():
    bpy.msgbus.clear_by_owner(MESSAGE_BROKER)
    bpy.app.handlers.load_post.remove(enable_message_broker)
    bpy.types.MESH_MT_shape_key_context_menu.remove(draw_menu_items)

    try:
        del bpy.types.Key.pose_drivers
    except: pass

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
