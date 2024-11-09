import bpy
from bpy.types import Object, PoseBone
from typing import Optional, Sequence

from rigify.utils.mechanism import (
    _set_default_attr,
    MechanismUtilityMixin as RigifyMechanismUtilityMixin
)
from rigify.utils.misc import force_lazy, ArmatureObject, Lazy, OptionalLazy        

def make_constraint(
        owner: Object | PoseBone, con_type: str,
        target: Optional[Object] = None,
        subtarget: OptionalLazy[str] = None, *,
        insert_index: Optional[int] = None,
        space: Optional[str] = None,
        track_axis: Optional[str] = None,
        use_xyz: Optional[Sequence[bool]] = None,
        use_limit_xyz: Optional[Sequence[bool]] = None,
        invert_xyz: Optional[Sequence[bool]] = None,
        min_xyz: Optional[Sequence[float]] = None,
        max_xyz: Optional[Sequence[float]] = None,
        targets: Optional[list[Lazy[str | tuple | dict]]] = None,
        **options):
    
    """
    Creates a new constraint on the given owner object or pose bone.

    Args:
        owner: The object or pose bone to add the constraint to.
        con_type: The type of constraint to create.
        target: The target object for the constraint (optional).
        subtarget: The subtarget for the constraint (optional).
        insert_index: The index at which to insert the constraint (optional).
        space: The space for the constraint (optional).
        track_axis: The track axis for the constraint (optional).
        use_xyz: A sequence of booleans indicating which axes to use (optional).
        use_limit_xyz: A sequence of booleans indicating which axes to limit (optional).
        invert_xyz: A sequence of booleans indicating which axes to invert (optional).
        min_xyz: A sequence of minimum values for the constraint (optional).
        max_xyz: A sequence of maximum values for the constraint (optional).
        targets: A list of target information for armature constraints (optional).
        **options: Additional keyword arguments to set on the constraint.

    Returns:
        The newly created constraint.
    """
    
    con = owner.constraints.new(con_type)

    # For Armature constraints, allow passing a "targets" list as a keyword argument.
    if targets is not None:
        assert isinstance(con, ArmatureConstraint)
        for target_info in targets:
            con_target = con.targets.new()
            con_target.target = owner.id_data
            # List element can be a string, a tuple or a dictionary.
            target_info = force_lazy(target_info)
            if isinstance(target_info, str):
                con_target.subtarget = target_info
            elif isinstance(target_info, tuple):
                if len(target_info) == 2:
                    con_target.subtarget, con_target.weight = map(force_lazy, target_info)
                else:
                    con_target.target, con_target.subtarget, con_target.weight = map(force_lazy, target_info)
            else:
                assert isinstance(target_info, dict)
                for key, val in target_info.items():
                    setattr(con_target, key, force_lazy(val))

    if insert_index is not None:
        owner.constraints.move(len(owner.constraints)-1, insert_index)

    if target is not None and hasattr(con, 'target'):
        con.target = target

    if subtarget is not None:
        con.subtarget = force_lazy(subtarget)

    if space is not None:
        _set_default_attr(con, options, 'owner_space', space)
        _set_default_attr(con, options, 'target_space', space)

    if track_axis is not None:
        con.track_axis = _TRACK_AXIS_MAP.get(track_axis, track_axis)

    if use_xyz is not None:
        con.use_x, con.use_y, con.use_z = use_xyz[0:3]

    if use_limit_xyz is not None:
        con.use_limit_x, con.use_limit_y, con.use_limit_z = use_limit_xyz[0:3]

    if invert_xyz is not None:
        con.invert_x, con.invert_y, con.invert_z = invert_xyz[0:3]
    # make one list option for min max
    if min_xyz is not None:
        for i, key in enumerate(['min_x', 'min_y', 'min_z']):
            options[key] = min_xyz[i]
    if max_xyz is not None:
        for i, key in enumerate(['max_x', 'max_y', 'max_z']):
            options[key] = max_xyz[i]

    for key in ['min_x', 'max_x', 'min_y', 'max_y', 'min_z', 'max_z']:
        if key in options:
            _set_default_attr(con, options, 'use_'+key, True)
            _set_default_attr(con, options, 'use_limit_'+key[-1], True)

    for p, v in options.items():
        setattr(con, p, force_lazy(v))

    return con


class MechanismUtilityMixin(RigifyMechanismUtilityMixin):

    """
    A mixin class that provides utility methods for working with armatures.

    Requires self.obj to be the armature object being worked on.
    """
    
    obj: ArmatureObject

    def make_constraint(self, bone: str, con_type: str,
                        subtarget: OptionalLazy[str] = None, *,
                        insert_index: Optional[int] = None,
                        space: Optional[str] = None,
                        track_axis: Optional[str] = None,
                        use_xyz: Optional[Sequence[bool]] = None,
                        use_limit_xyz: Optional[Sequence[bool]] = None,
                        invert_xyz: Optional[Sequence[bool]] = None,
                        min_xyz: Optional[Sequence[float]] = None,
                        max_xyz: Optional[Sequence[float]] = None,
                        targets: Optional[list[Lazy[str | tuple | dict]]] = None,
                        **args):
        """
        Creates a new constraint on the given bone of the armature.

        Args:
            bone: The name of the bone to add the constraint to.
            con_type: The type of constraint to create.
            subtarget: The subtarget for the constraint (optional).
            insert_index: The index at which to insert the constraint (optional).
            space: The space for the constraint (optional).
            track_axis: The track axis for the constraint (optional).
            use_xyz: A sequence of booleans indicating which axes to use (optional).
            use_limit_xyz: A sequence of booleans indicating which axes to limit (optional).
            invert_xyz: A sequence of booleans indicating which axes to invert (optional).
            min_xyz: A sequence of minimum values for the constraint (optional).
            max_xyz: A sequence of maximum values for the constraint (optional).
            targets: A list of target information for armature constraints (optional).
            **args: Additional keyword arguments to set on the constraint.

        Returns:
            The newly created constraint.
        """
        
        assert(self.obj.mode == 'OBJECT')
        return make_constraint(
            self.obj.pose.bones[bone], con_type, self.obj, subtarget,
            insert_index=insert_index, space=space, track_axis=track_axis,
            use_xyz=use_xyz, use_limit_xyz=use_limit_xyz, invert_xyz=invert_xyz,
            targets=targets,
            **args)
        

