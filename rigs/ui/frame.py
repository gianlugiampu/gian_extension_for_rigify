import bpy
from mathutils import Matrix

from rigify.base_rig import BaseRig, RigUtility
from rigify.utils.naming import strip_org
from rigify.utils.layers import ControlLayersOption
from rigify import base_generate

from ...utils.wgt import createFrameWidget, fixFrameWidget

from typing import Optional

class Rig(BaseRig, RigUtility, base_generate.BaseGenerator):

    """
    A rig class for creating a slider rig.

    Attributes:
        bones: A dictionary of bones in the rig.
        org_name: The name of the original bone.
    """
    
    bones: BaseRig.ToplevelBones[str, 'Rig.CtrlBones', str, str]
    org_name: str
       
    class CtrlBones(BaseRig.CtrlBones):

        """
        A class for control bones in the rig.

        Attributes:
            master: The main property control bone.
            panel: The panel bone.
        """
        
        master: str                    # Main property control.
        panel: str                     # Panel.
        
    def find_org_bones(self, pose_bone) -> str:

        """
        Finds the original bone name.

        Args:
            pose_bone: The pose bone to find the original bone for.

        Returns:
            The original bone name.
        """
        
        return pose_bone.name
    
    def getChildrenList(self):

        if self.obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        parent_master = self.obj.pose.bones[self.bones.org]
        
        children_list = []

        for b in self.obj.pose.bones:
            if b.parent == parent_master:
                children_list.append(b)
                print(b.name)

        if self.obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        return children_list

    def initialize(self):

        """
        Initializes the rig by gathering and validating data.
        """

        super().initialize()
        self.org_name = strip_org(self.bones.org)

        bone = self.get_bone(self.bones.org)
        self.range = bone.length

        self.title = self.params.title
        self.custom_title = self.params.custom_title

        parent = self.getChildrenList()
        print(parent)
        self.parent_list = parent.copy() 
    
    def generate_bones(self):

        """
        Generates the bones for the rig.
        """
        
        bones = self.bones
        
        # Make a control bone (copy of original).
        self.bones.ctrl.master = self.copy_bone(bones.org, self.org_name, length=self.range)

    def parent_bones(self):
        
        """
        Parents the bones in the rig.
        """

        bones = self.bones
        master_parent = self.get_bone_parent(self.bones.org)

        if master_parent != None:
            self.set_bone_parent(self.bones.ctrl.master, master_parent)

    def configure_bones(self):

        """
        Configures the bones in the rig.
        """
        
        bones = self.bones
        self.copy_bone_properties(bones.org, bones.ctrl.master)
        self.get_bone(bones.ctrl.master).use_custom_shape_bone_size = False
    
    def rig_bones(self):

        """
        Rigs the bones in the rig.
        """
        
        bones = self.bones
    
    def generate_widgets(self):

        """
        Generates the widgets for the rig.
        """

        bones = self.bones
        params = self.params
        par = self.parent_list

        frame_bone = self.get_bone(bones.ctrl.master)
        frame_head = frame_bone.head

        # Create control widget:
        frame_wgt = createFrameWidget(self.obj, par, self.title, self.custom_title, frame_head, rig=self.obj, bone_name=bones.ctrl.master, bone_transform_name=None)
        
        # fixFrameWidget(frame_wgt, self.obj, par, self.title, self.custom_title, frame_head)

        bpy.context.view_layer.objects.active = self.obj   

    @classmethod
    def add_parameters(cls, params):

        """
        Adds the parameters of this rig type to the RigifyParameters PropertyGroup.

        Args:
            params: The RigifyParameters PropertyGroup.
        """

        super().add_parameters(params)
        
        params.title = bpy.props.BoolProperty(name='Title', default=True)
        params.custom_title = bpy.props.StringProperty(name="Custom Title", default='')

    @classmethod
    def parameters_ui(cls, layout, params):
        
        """
        Creates the UI for the rig parameters.

        Args:
            layout: The UI layout.
            params: The RigifyParameters PropertyGroup.
        """

        super().parameters_ui(layout, params)

        col = layout.column()
        col.label(text="Create a frame around its children bones!", icon='INFO')

        col.prop(params, "title")
        
        if params.title:
            col.prop(params, "custom_title")


def set_params(pbone, attr, value):

    """
    Sets a parameter on a pose bone.

    Args:
        pbone: The pose bone.
        attr: The attribute to set.
        value: The value to set the attribute to.
    """

    if hasattr(pbone.rigify_parameters, attr):
        setattr(pbone.rigify_parameters, attr, value)

def create_sample(obj):
    
    """
    Creates a sample metarig for this rig type.

    Args:
        obj: The object to create the metarig for.

    Returns:
        A dictionary of bones in the metarig.
    """
    
    # generated by rigify.utils.write_metarig
    bpy.ops.object.mode_set(mode='EDIT')
    arm = obj.data

    bones = {}

    bone = arm.edit_bones.new('Bone')
    bone.head[:] = 0.0000, 0.0000, 0.0000
    bone.tail[:] = 0.0000, 0.0000, 0.2000
    bone.roll = 0.0000
    bone.use_connect = False
    bones['Bone'] = bone.name

    bpy.ops.object.mode_set(mode='OBJECT')
    pbone = obj.pose.bones[bones['Bone']]
    pbone.lock_location = (False, False, False)
    pbone.lock_rotation = (False, False, False)
    pbone.lock_rotation_w = False
    pbone.lock_scale = (False, False, False)
    pbone.rotation_mode = 'QUATERNION'
    set_params(pbone, "custom_text", 'text')
        
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.edit_bones:
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
    for b in bones:
        bone = arm.edit_bones[bones[b]]
        bone.select = True
        bone.select_head = True
        bone.select_tail = True
        arm.edit_bones.active = bone

    return bones