
from functools import partial
from typing import Callable, List, Sequence, Tuple, TYPE_CHECKING
from math import acos, asin, fabs, pi, sqrt
import numpy as np
from pose_driven_shape_keys.api.shape_key import PoseDrivenShapeKey
if TYPE_CHECKING:
    from bpy.types import DriverTarget
    from ..api.group import PoseDrivenShapeKeyGroup

# No normalization is necessary, just distance and radius

def distance_euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum(pow(ai-bi,2.0) for ai,bi in zip(a,b)))


def distance_angle(a: Sequence[float], b: Sequence[float]) -> float:
    return fabs(a[0]-b[0])/pi


def distance_quaternion(a: Sequence[float], b: Sequence[float]) -> float:
    return acos((2.0*pow(min(max(sum(ai*bi for ai,bi in zip(a,b)),-1.0),1.0),2.0))-1.0)/pi


def distance_direction(a: Sequence[float], b: Sequence[float], axis: str) -> float:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    if axis == 'X':
        a = (1.0-2.0*(ay*ay+az*az),2.0*(ax*ay+aw*az),2.0*(ax*az-aw*ay))
        b = (1.0-2.0*(by*by+bz*bz),2.0*(bx*by+bw*bz),2.0*(bx*bz-bw*by))
    elif axis == 'Y':
        a = (2.0*(ax*ay-aw*az),1.0-2.0*(ax*ax+az*az),2.0*(ay*az+aw*ax))
        b = (2.0*(bx*by-bw*bz),1.0-2.0*(bx*bx+bz*bz),2.0*(by*bz+bw*bx))
    else:
        a = (2.0*(ax*az+aw*ay),2.0*(ay*az-aw*ax),1.0-2.0*(ax*ax+ay*ay))
        b = (2.0*(bx*bz+bw*by),2.0*(by*bz-bw*bx),1.0-2.0*(bx*bx+by*by))
    return (asin((sum(ai*bi for ai,bi in zip(a,b))))--(pi/2.0))/pi


def distance_direction_x(a: Sequence[float], b: Sequence[float]) -> float:
    return distance_direction(a, b, 'X')


def distance_direction_y(a: Sequence[float], b: Sequence[float]) -> float:
    return distance_direction(a, b, 'Y')


def distance_direction_z(a: Sequence[float], b: Sequence[float]) -> float:
    return distance_direction(a, b, 'Z')


def distance_matrix_(params: np.ndarray,
                     metric: Callable[[Sequence[float], Sequence[float]], float]) -> np.ndarray:
    matrix = np.array((len(params), len(params)), dtype=float)
    for a, row in zip(params, matrix):
        for i, b in enumerate(params):
            row[i] = metric(a, b)
    return matrix


def distance_matrix(group: PoseDrivenShapeKeyGroup) -> np.ndarray:
    items: List[PoseDrivenShapeKey] = list(group)
    stack = []
    
    flags = (group.location_x,
             group.location_y,
             group.location_z)

    if any(flags):
        params = np.array([x.location for x in items], dtype=float)
        if not all(flags):
            params = params.T
            params = np.array([params[i] for i, x in enumerate(flags) if x], dtype=float).T
        stack.append(distance_matrix_(params, distance_euclidean))

    if group.rotation_mode == 'EULER':
        flags = (group.rotation_x,
                 group.rotation_y,
                 group.rotation_z)

        if any(flags):
            params = np.array([x.rotation_euler for x in items], dtype=float)
            if not all(flags):
                params = params.T
                params = np.array([params[i] for i, x in enumerate(flags) if x], dtype=float).T
            stack.append(distance_matrix_(params, distance_euclidean))

    elif group.rotation:
        mode = group.rotation_mode

        if mode == 'TWIST':
            axis = group.rotation_axis
            params = np.array([x.rotation_quaternion.to_swing_twist(axis)[1] for x in items], dtype=float)
            metric = distance_angle
        else:
            params = np.array([x.rotation_quaternion for x in items], dtype=float)
            if mode == 'SWING':
                metric = partial(distance_direction, axis=group.rotation_axis)
            else:
                metric = distance_quaternion

        stack.append(distance_matrix_(params, metric))

    flags = (group.scale_x,
             group.scale_y,
             group.scale_z)

    if any(flags):
        params = np.array([x.scale for x in items], dtype=float)
        if not all(flags):
            params = params.T
            params = np.array([params[i] for i, x in enumerate(flags) if x], dtype=float).T
        stack.append(distance_matrix_(params, distance_euclidean))

    params = []
    for key in ('bbone_curveinx',
                'bbone_curveinz',
                'bbone_curveoutx',
                'bbone_curveoutz',
                'bbone_easein',
                'bbone_easeout',
                'bbone_rollin',
                'bbone_rollout',
                'bbone_scaleinx',
                'bbone_scaleiny',
                'bbone_scaleinz',
                'bbone_scaleoutx',
                'bbone_scaleouty',
                'bbone_scaleoutz'):
        if getattr(group, key):
            params.append([getattr(x, key) for x in items])

    if params:
        params = np.array(params, dtype=float)
        for data in params:
            norm = np.linalg.norm(data)
            if norm != 0.0:
                data /= norm
        stack.append(distance_matrix_(params.T, distance_euclidean))

    if len(stack) == 1:
        matrix = stack[0]
    else:
        matrix = np.add.reduce(stack, axis=1)
        matrix /= float(len(stack))

    return matrix


def pose_radii(distance_matrix: np.ndarray) -> Sequence[float]:
    radii = []
    for row in np.ma.masked_values(distance_matrix, 0.0, atol=0.001):
        row = row.compressed()
        radii.append(0.0 if len(row) == 0 else np.min(row))
    return radii


def expression_euclidean(tokens: Sequence[Tuple[str, str]]) -> str:
    return f'sqrt({"+".join("pow("+a+"-"+b+",2.0)" for a,b in tokens)})'


def expression_quaternion(tokens: Sequence[Tuple[str, str]]) -> str:
    return f'acos((2.0*pow(clamp({"+".join(["*".join(x) for x in tokens])},-1.0,1.0),2.0))-1.0)/pi'


def expression_swing(tokens: Tuple[float, float, float, float], axis: str) -> str:
    w, x, y, z = tokens
    if axis == 'X':
        a = str(1.0-2.0*(y*y+z*z))
        b = str(2.0*(x*y+w*z))
        c = str(2.0*(x*z-w*y))
        e = f'(asin((1.0-2.0*(y*y+z*z))*{a}+2.0*(x*y+w*z)*{b}+2.0*(x*z-w*y)*{c})-(pi/2.0))/pi'
    elif axis == 'Y':
        a = str(2.0*(x*y-w*z))
        b = str(1.0-2.0*(x*x+z*z))
        c = str(2.0*(y*z+w*x))
        e = f'(asin(2.0*(x*y-w*z)*{a}+(1.0-2.0*(x*x+z*z))*{b}+2.0*(y*z+w*x)*{c})--(pi/2.0))/pi'
    else:
        a = str(2.0*(x*z+w*y))
        b = str(2.0*(y*z-w*x))
        c = str(1.0-2.0*(x*x+y*y))
        e = f'(asin(2.0*(x*z+w*y)*{a}+2.0*(y*z-w*x)*{b}+(1.0-2.0*(x*x+y*y))*{c})--(pi/2.0))/pi'
    return e


def expression_swing(tokens: Sequence[Tuple[str, float]]) -> None:
    return f'fabs({tokens[0][0]}-{str(tokens[0][1])})/pi'


def target_assign__transform(type: str, target: 'DriverTarget', group: 'PoseDrivenShapeKeyGroup') -> None:
    target.id = group.object
    target.bone_target = group.bone_target
    target.transform_type = type
    target.transform_space = 'LOCAL_SPACE'
    if type.startswith('ROT'):
        target.rotation_mode = group.rotation_mode


def target_assign__bboneprop(path: str, target: 'DriverTarget', group: 'PoseDrivenShapeKeyGroup') -> None:
    target.id = group.object
    target.data_path = f'pose.bones["{group.bone_target}"].{path}'


def group_update__fcurves(group: 'PoseDrivenShapeKeyGroup') -> None:
    matrix = distance_matrix(group)
