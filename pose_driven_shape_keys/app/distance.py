
from typing import Callable, List, Sequence, TYPE_CHECKING
from functools import partial
from math import acos, asin, fabs, pi, sqrt
import numpy as np
if TYPE_CHECKING:
    from ..api.group import PoseDrivenShapeKeyGroup
    from ..api.shape_key import PoseDrivenShapeKey

def euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum(pow(ai-bi,2.0) for ai,bi in zip(a,b)))


def angle(a: Sequence[float], b: Sequence[float]) -> float:
    return fabs(a[0]-b[0])/pi


def quaternion(a: Sequence[float], b: Sequence[float]) -> float:
    return acos((2.0*pow(min(max(sum(ai*bi for ai,bi in zip(a,b)),-1.0),1.0),2.0))-1.0)/pi


def direction(a: Sequence[float], b: Sequence[float], axis: str) -> float:
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


def direction_x(a: Sequence[float], b: Sequence[float]) -> float:
    return direction(a, b, 'X')


def direction_y(a: Sequence[float], b: Sequence[float]) -> float:
    return direction(a, b, 'Y')


def direction_z(a: Sequence[float], b: Sequence[float]) -> float:
    return direction(a, b, 'Z')


def matrix_(params: np.ndarray,
            metric: Callable[[Sequence[float], Sequence[float]], float]) -> np.ndarray:
    matrix = np.array((len(params), len(params)), dtype=float)
    for a, row in zip(params, matrix):
        for i, b in enumerate(params):
            row[i] = metric(a, b)
    return matrix


def matrix(group: PoseDrivenShapeKeyGroup) -> np.ndarray:
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
        stack.append(matrix_(params, euclidean))

    if group.rotation_mode == 'EULER':
        flags = (group.rotation_x,
                 group.rotation_y,
                 group.rotation_z)

        if any(flags):
            params = np.array([x.rotation_euler for x in items], dtype=float)
            if not all(flags):
                params = params.T
                params = np.array([params[i] for i, x in enumerate(flags) if x], dtype=float).T
            stack.append(matrix_(params, euclidean))

    elif group.rotation:
        mode = group.rotation_mode

        if mode == 'TWIST':
            axis = group.rotation_axis
            params = np.array([x.rotation_quaternion.to_swing_twist(axis)[1] for x in items], dtype=float)
            metric = angle
        else:
            params = np.array([x.rotation_quaternion for x in items], dtype=float)
            if mode == 'SWING':
                metric = partial(direction, axis=group.rotation_axis)
            else:
                metric = quaternion

        stack.append(matrix_(params, metric))

    flags = (group.scale_x,
             group.scale_y,
             group.scale_z)

    if any(flags):
        params = np.array([x.scale for x in items], dtype=float)
        if not all(flags):
            params = params.T
            params = np.array([params[i] for i, x in enumerate(flags) if x], dtype=float).T
        stack.append(matrix_(params, euclidean))

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
        stack.append(matrix_(params.T, euclidean))

    if len(stack) == 1:
        matrix = stack[0]
    else:
        matrix = np.add.reduce(stack, axis=1)
        matrix /= float(len(stack))

    return matrix