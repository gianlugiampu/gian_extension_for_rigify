import bpy
import math
import inspect
import functools
import mathutils

from typing import Optional, Callable, TYPE_CHECKING
from bpy.types import Mesh, Object, UILayout, WindowManager
from mathutils import Matrix, Vector, Euler
from itertools import count

from rigify.base_generate import BaseGenerator
from rigify.utils.collections import ensure_collection
from rigify.utils.naming import change_name_side, get_name_side, Side
from rigify.utils.errors import MetarigError
from rigify.utils.misc import ArmatureObject, MeshObject, AnyVector, verify_mesh_obj, IdPropSequence

from rigify.feature_set_list import get_install_path, get_enabled_modules_names

WGT_PREFIX = "WGT-"  # Prefix for widget objects
WGT_GROUP_PREFIX = "WGTS_"  # noqa; Prefix for the widget collection

from mathutils import Matrix

from rigify.utils.widgets import (
  create_widget, widget_generator, 
  adjust_widget_axis, adjust_widget_transform_mesh
)

from rigify.utils.bones import get_bone

"""
CUSTOM RIGIFY FUNCTIONS
"""
def custom_obj_to_bone(obj: Object, rig: ArmatureObject, bone_name: str,
                bone_transform_name: Optional[str] = None):
    """ Places an object at the location/rotation/scale of the given bone.
    """
    if bpy.context.mode == 'EDIT_ARMATURE':
        raise MetarigError("obj_to_bone(): does not work while in edit mode")

    bone = rig.pose.bones[bone_name]

    loc = bone.custom_shape_translation
    rot = bone.custom_shape_rotation_euler
    scale = Vector(bone.custom_shape_scale_xyz)

    if bone.use_custom_shape_bone_size:
        scale *= bone.length

    if bone_transform_name is not None:
        bone = rig.pose.bones[bone_transform_name]
    elif bone.custom_shape_transform:
        bone = bone.custom_shape_transform

    shape_mat = Matrix.LocRotScale(loc, Euler(rot), scale)

    obj.rotation_mode = 'XYZ'
    obj.matrix_basis = rig.matrix_world @ bone.bone.matrix_local @ shape_mat

def custom_create_widget(rig: ArmatureObject, bone_name: str,
                  bone_transform_name: Optional[str] = None, *,
                  widget_name: Optional[str] = None, mir=False,
                  widget_force_new=False, subsurf=0) -> Optional[MeshObject]:
    """
    Creates an empty widget object for a bone, and returns the object.
    If the object already existed, returns None.
    """
    assert rig.mode != 'EDIT'

    scene = bpy.context.scene
    bone = rig.pose.bones[bone_name]

    # Access the current generator instance when generating (ugh, globals)
    generator = BaseGenerator.instance

    if generator:
        collection = generator.widget_collection
    else:
        collection = ensure_collection(bpy.context, WGT_GROUP_PREFIX + rig.name, hidden=True)

    use_mirror = mir
    bone_mid_name = change_name_side(bone_name, Side.MIDDLE) if use_mirror else bone_name

    obj_name = widget_name or WGT_PREFIX + rig.name + '_' + bone_name
    reuse_mesh = None

    obj: Optional[MeshObject]

    # Check if it already exists in the scene
    if not widget_force_new:
        obj = None

        if generator:
            # Check if the widget was already generated
            if bone_name in generator.new_widget_table:
                return None

            # If re-generating, check widgets used by the previous rig
            obj = generator.old_widget_table.get(bone_name)

        if not obj:
            # Search the scene by name
            obj = scene.objects.get(obj_name)
            if obj and obj.library:
                # Second brute force try if the first result is linked
                local_objs = [obj for obj in scene.objects
                              if obj.name == obj_name and not obj.library]
                obj = local_objs[0] if local_objs else None

        if obj:
            # Record the generated widget
            if generator:
                generator.new_widget_table[bone_name] = obj

            # Re-add to the collection if not there for some reason
            if obj.name not in collection.objects:
                collection.objects.link(obj)

            # Flip scale for originally mirrored widgets
            if obj.scale.x < 0 < bone.custom_shape_scale_xyz.x:
                bone.custom_shape_scale_xyz.x *= -1

            # Move object to bone position, in case it changed
            custom_obj_to_bone(obj, rig, bone_name, bone_transform_name)

            return None

        # Create a linked duplicate of the widget assigned in the metarig
        reuse_widget = rig.pose.bones[bone_name].custom_shape
        if reuse_widget:
            subsurf = 0
            reuse_mesh = reuse_widget.data

        # Create a linked duplicate with the mirror widget
        if not reuse_mesh and use_mirror and bone_mid_name != bone_name:
            reuse_mesh = generator.widget_mirror_mesh.get(bone_mid_name)

    # Create an empty mesh datablock if not linking
    if reuse_mesh:
        mesh = reuse_mesh

    elif use_mirror and bone_mid_name != bone_name:
        # When mirroring, untag side from mesh name, and remember it
        mesh = bpy.data.meshes.new(change_name_side(obj_name, Side.MIDDLE))

        generator.widget_mirror_mesh[bone_mid_name] = mesh

    else:
        mesh = bpy.data.meshes.new(obj_name)

    # Create the object
    obj = verify_mesh_obj(bpy.data.objects.new(obj_name, mesh))
    collection.objects.link(obj)

    # Add the subdivision surface modifier
    # if subsurf > 0:
    #     mod = obj.modifiers.new("subsurf", 'SUBSURF')
    #     mod.levels = subsurf

    # Record the generated widget
    if generator:
        generator.new_widget_table[bone_name] = obj

    # Flip scale for right side if mirroring widgets
    if use_mirror and get_name_side(bone_name) == Side.RIGHT:
        if bone.custom_shape_scale_xyz.x > 0:
            bone.custom_shape_scale_xyz.x *= -1

    # Move object to bone position and set layers
    custom_obj_to_bone(obj, rig, bone_name, bone_transform_name)

    if reuse_mesh:
        return None

    return obj

"""
MY FUNCTIONS
"""

def importBoxNode():

    node_name = 'GN-wgt_Box'

    gen_path = get_install_path()
    active_modules = [mod for mod in get_enabled_modules_names() if 'gian' in mod][0]
    full_path = gen_path + '/' + active_modules

    path = full_path + '/utils/widget_blend/custom_wgts.blend'

    with bpy.data.libraries.load(path) as (data_from, data_to):    
        data_to.node_groups.append(node_name)
        
    node_group = bpy.data.node_groups.get(node_name)
    
    return node_group

def importControlNode():
    
    node_name = 'GN-wgt_Ctrl'

    gen_path = get_install_path()
    active_modules = [mod for mod in get_enabled_modules_names() if 'gian' in mod][0]
    full_path = gen_path + '/' + active_modules

    path = full_path + '/utils/widget_blend/custom_wgts.blend'

    with bpy.data.libraries.load(path) as (data_from, data_to):    
        data_to.node_groups.append(node_name)
        
    node_group = bpy.data.node_groups.get(node_name)
    
    return node_group

def importTextNode():
    
    node_name = 'GN-wgt_Text'

    gen_path = get_install_path()
    active_modules = [mod for mod in get_enabled_modules_names() if 'gian' in mod][0]
    full_path = gen_path + '/' + active_modules

    path = full_path + '/utils/widget_blend/custom_wgts.blend'

    with bpy.data.libraries.load(path) as (data_from, data_to):    
        data_to.node_groups.append(node_name)
        
    node_group = bpy.data.node_groups.get(node_name)
    
    return node_group

def importFrameNode():
    
    node_name = 'GN-wgt_Frame'

    gen_path = get_install_path()
    active_modules = [mod for mod in get_enabled_modules_names() if 'gian' in mod][0]
    full_path = gen_path + '/' + active_modules

    path = full_path + '/utils/widget_blend/custom_wgts.blend'

    with bpy.data.libraries.load(path) as (data_from, data_to):    
        data_to.node_groups.append(node_name)
        
    node_group = bpy.data.node_groups.get(node_name)
    
    return node_group

def boxWidget(wgt, type, clp, txt, min, fill):

    node = None

    if not 'GN-wgt_Box' in bpy.data.node_groups:
        node = importBoxNode()
    
    else:
        node = bpy.data.node_groups['GN-wgt_Box']

    # # Create a new mesh
    # mesh = bpy.data.meshes.new(wgt_name)

    # # Create a new object using the mesh
    # obj = bpy.data.objects.new(wgt_name, mesh)

    # # Add the object to the scene
    # scene = bpy.context.scene
    # scene.collection.objects.link(obj)
    
    mod = wgt.modifiers.new(node.name, type='NODES')
    mod.node_group = node
    
    #setup variables for updates
    radius_input = 'Socket_4'
    box_x_input = 'Socket_5'
    clamp_input = 'Socket_8'
    text_input = 'Socket_13'
    minimal_input = 'Socket_16'
    fill_input = 'Socket_7'
    
    type_value = 1.0 if type == 'LARGE' else 0.0
    clp_value = {'NONE': 0, 'UP': 1}.get(clp, 2)
    
    wgt.modifiers[mod.name][box_x_input] = type_value
    wgt.modifiers[mod.name][clamp_input] = clp_value
    wgt.modifiers[mod.name][text_input] = txt
    wgt.modifiers[mod.name][minimal_input] = min
    wgt.modifiers[mod.name][fill_input] = fill
    
    #Update Node Values on modifier
    mod.node_group.interface_update(bpy.context)

    sub = wgt.modifiers.new("subsurf", 'SUBSURF')
    sub.levels = 1
    
    # bpy.context.view_layer.objects.active = obj
    # bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # bpy.data.node_groups.remove(bpy.data.node_groups['GN-wgt_Box'])

    return wgt

def ctrlWidget(wgt, fill, offset):

    node = None

    if not 'GN-wgt_Ctrl' in bpy.data.node_groups:
        node = importControlNode()
    
    else:
        node = bpy.data.node_groups['GN-wgt_Ctrl']

    mod = wgt.modifiers.new(node.name, type='NODES')
    mod.node_group = node

    #setup variables for updates    
    radius_input = 'Socket_4'
    fill_control = 'Socket_7'
    offset_input = 'Socket_14'

    wgt.modifiers[mod.name][fill_control] = fill
    wgt.modifiers[mod.name][offset_input] = offset_input
    
    #Update Node Values on modifier
    mod.node_group.interface_update(bpy.context)

    sub = wgt.modifiers.new("subsurf", 'SUBSURF')
    sub.levels = 1
    
    # bpy.context.view_layer.objects.active = obj
    # bpy.ops.object.modifier_apply(modifier=mod.name)
    # bpy.data.node_groups.remove(bpy.data.node_groups['GN-wgt_Ctrl'])

    return wgt

def textWidget(wgt, txt):

    node = None

    if not 'GN-wgt_Text' in bpy.data.node_groups:
        node = importTextNode()
    
    else:
        node = bpy.data.node_groups['GN-wgt_Text']

    mod = wgt.modifiers.new(node.name, type='NODES')
    mod.node_group = node
    
    #setup variables for updates
    text_input = 'Socket_3'
    
    wgt.modifiers[mod.name][text_input] = txt
    
    #Update Node Values on modifier
    mod.node_group.interface_update(bpy.context)
    
    # bpy.context.view_layer.objects.active = wgt
    # bpy.ops.object.modifier_apply(modifier=mod.name)
    
    # bpy.data.node_groups.remove(bpy.data.node_groups['GN-wgt_Text'])

    return wgt

def frameWidget(wgt, meta, children, tlt, csm_text, start_pos):

    output_obj = []

    wgt_name = wgt.name

    if len(children) > 1:

        og_mode = meta.mode

        if meta.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        vectors = []

        for b in children:
            vectors.append(b.head)
            vectors.append(b.tail)
            print('vector' + b.name)

        min_x = min(v.x for v in vectors)
        max_x = max(v.x for v in vectors)

        min_z = min(v.z for v in vectors)
        max_z = max(v.z for v in vectors)

        if meta.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create a new mesh and object
        mesh = bpy.data.meshes.new(f'{wgt_name}_FR')
        obj = bpy.data.objects.new(f'{wgt_name}_FR', mesh)

        # Create vertices, edges, and faces for the mesh
        # Add offset to min and max values

        start_x = start_pos.x
        start_z = start_pos.z

        print(start_x, start_z)

        offset_x = (max_x - min_x) *0.1
        offset_z = (max_z - min_z) *0.1

        min_x_offset = (min_x - offset_x) - start_x
        max_x_offset = (max_x + offset_x) - start_x
        min_y_offset = (min_z - offset_z) - start_z
        max_y_offset = (max_z + offset_z) - start_z

        verts = [(min_x_offset, min_y_offset, 0), (max_x_offset, min_y_offset, 0), 
                (max_x_offset, max_y_offset, 0), (min_x_offset, max_y_offset, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        faces = []

        # Create the mesh from the vertices, edges, and faces
        mesh.from_pydata(verts, edges, faces)
        mesh.update()

        # Add the object to the scene
        scene = bpy.context.scene
        scene.collection.objects.link(obj)        

        if meta.mode != og_mode:
            bpy.ops.object.mode_set(mode=og_mode)
        
        wgt.data = mesh
        bpy.data.objects.remove(obj)
    else:
        
        og_mode = meta.mode

        if meta.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Create a new mesh and object
        mesh = bpy.data.meshes.new(f'{wgt_name}_FR')
        obj = bpy.data.objects.new(f'{wgt_name}_FR', mesh)

        # Create vertices, edges, and faces for the mesh
        min_x_offset = -1
        max_x_offset = 1
        min_y_offset = -1
        max_y_offset = 1

        verts = [(min_x_offset, min_y_offset, 0), (max_x_offset, min_y_offset, 0), 
                (max_x_offset, max_y_offset, 0), (min_x_offset, max_y_offset, 0)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        faces = []

        # Create the mesh from the vertices, edges, and faces
        mesh.from_pydata(verts, edges, faces)
        mesh.update()

        # Add the object to the scene
        scene = bpy.context.scene
        scene.collection.objects.link(obj)

        if meta.mode != og_mode:
            bpy.ops.object.mode_set(mode=og_mode)
        
        wgt.data = mesh
        bpy.data.objects.remove(obj)

    if tlt:

        node = None

        if not 'GN-wgt_Frame' in bpy.data.node_groups:
            node = importFrameNode()
        
        else:
            node = bpy.data.node_groups['GN-wgt_Frame']
        
        mod = wgt.modifiers.new(node.name, type='NODES')
        mod.node_group = node
        
        #setup variables for updates
        custom_title_input = 'Socket_2'
        
        wgt.modifiers[mod.name][custom_title_input] = csm_text
        
        #Update Node Values on modifier
        mod.node_group.interface_update(bpy.context)
        
        # bpy.context.view_layer.objects.active = wgt
        # bpy.ops.object.modifier_apply(modifier=mod.name)
        
        # bpy.data.node_groups.remove(bpy.data.node_groups['GN-wgt_Frame'])

        return wgt

    else:
        return wgt

def createBoxWidget(rig, bone_name, design, clp, txt, minimal, fill, bone_transform_name=None):

    obj = custom_create_widget(rig, bone_name, bone_transform_name, mir=False, subsurf=1)    

    if obj != None:
        dref_obj = boxWidget(obj, design, clp, txt, minimal, fill)

        # obj.data = dref_obj.data
        #bpy.data.objects.remove(dref_obj)
        # obj.data.name = obj.name
    
        return obj

def createControlWidget(rig, bone_name, fill_it, off, bone_transform_name=None):
  
    obj = custom_create_widget(rig, bone_name, bone_transform_name, mir=False, subsurf=1)
    
    if obj != None:
        dref_obj = ctrlWidget(obj, fill=fill_it, offset=off)

        # obj.data = dref_obj.data
        #bpy.data.objects.remove(dref_obj)

        # obj.data.name = obj.name 
    
        return obj
    
def createTextWidget(txt, rig, bone_name, bone_transform_name=None):

    obj = custom_create_widget(rig, bone_name, bone_transform_name, mir=False, subsurf=1)

    if obj != None:
        dref_obj = textWidget(obj, txt)

        # obj.data = dref_obj.data
        # bpy.data.objects.remove(dref_obj)

        # obj.data.name = obj.name
    
        return obj

    return obj
    
def createFrameWidget(metarig, list, title, custom_tlt, head_b, rig, bone_name, bone_transform_name=None):

    obj = custom_create_widget(rig, bone_name, bone_transform_name, mir=False, subsurf=0)

    if obj != None:
        dref_obj = frameWidget(obj, metarig, list, title, custom_tlt, head_b)

        # obj.data = dref_obj.data
        # bpy.data.objects.remove(dref_obj)

        # obj.data.name = obj.name
    
        return obj

    return obj
    
def fixBoxWidget(obj, design, clp, txt, minimal, fill):

    if obj != None:
        dref_obj = boxWidget(obj.name, design, clp, txt, minimal, fill)

        obj.data = dref_obj.data
        bpy.data.objects.remove(dref_obj)

        obj.data.name = obj.name
    
        return obj
    
def fixControlWidget(obj, fill_it, off):

    if obj != None:
        dref_obj = ctrlWidget(obj.name, fill=fill_it, offset=off)

        obj.data = dref_obj.data
        bpy.data.objects.remove(dref_obj)

        obj.data.name = obj.name 
    
        return obj
    
def fixTextWidget(obj, txt):

    if obj != None:
        dref_obj = textWidget(obj.name, txt)

        obj.data = dref_obj.data
        bpy.data.objects.remove(dref_obj)

        obj.data.name = obj.name
    
        return obj
    
def fixFrameWidget(obj, metarig, list, title, custom_tlt, head_b):

    if obj != None:
        dref_obj = frameWidget(obj.name, metarig, list, title, custom_tlt, head_b)

        obj.data = dref_obj.data
        bpy.data.objects.remove(dref_obj)

        obj.data.name = obj.name
    
        return obj