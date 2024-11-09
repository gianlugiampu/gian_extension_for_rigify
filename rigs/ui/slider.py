import bpy
from mathutils import Matrix

from rigify.base_rig import BaseRig
from rigify.utils.naming import strip_org
from rigify.utils.bones import set_bone_orientation
from rigify.rigs.basic.raw_copy import RelinkConstraintsMixin
from rigify.utils.layers import ControlLayersOption

from ...utils.wgt import createBoxWidget, createControlWidget, fixBoxWidget, fixControlWidget
from ...utils.mech import make_constraint

class Rig(BaseRig, RelinkConstraintsMixin):

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

    def initialize(self):

        """
        Initializes the rig by gathering and validating data.
        """

        super().initialize()
        self.org_name = strip_org(self.bones.org)
        
        self.slider_type = self.params.slider_type
        self.clamp_up_down = self.params.clamp_up_down
        self.custom_title = self.params.custom_title
        self.fill_slider = self.params.fill_slider
        self.minimal_design = self.params.minimal_design
        self.fill_pan = self.params.fill_pan

        bone = self.get_bone(self.bones.org)
        self.range = bone.length
    
    def generate_bones(self):

        """
        Generates the bones for the rig.
        """
        
        bones = self.bones      
        
        # Make a control bone (copy of original).
        self.bones.ctrl.master = self.copy_bone(bones.org, self.org_name, parent=True, length=self.range)
        self.bones.ctrl.panel = self.copy_bone(bones.org, f"PAN_{self.org_name}", length=self.range)                

        if 'LARGE' in self.slider_type:
          # Change the bone orientation to default if it is LARGE
          m = Matrix(((1.0, 0.0, 0.0, 0.0),
                      (0.0, 0.0, -1.0, 0.0),
                      (0.0, 1.0, 0.0, 0.0),
                      (0.0, 0.0, 0.0, 1.0))) # Y up bone
          set_bone_orientation(self.obj, self.bones.ctrl.master, m)
          set_bone_orientation(self.obj, self.bones.ctrl.panel, m)

    def parent_bones(self):
        
        """
        Parents the bones in the rig.
        """

        bones = self.bones
        new_parent = self.relink_bone_parent(bones.org)
        self.set_bone_parent(bones.ctrl.master, bones.ctrl.panel)
        if new_parent:
            self.set_bone_parent(bones.ctrl.panel, new_parent)

    def configure_bones(self):

        """
        Configures the bones in the rig.
        """
                
        bones = self.bones
        self.copy_bone_properties(bones.org, bones.ctrl.master)
        self.get_bone(bones.ctrl.master).use_custom_shape_bone_size = True
        self.get_bone(bones.ctrl.panel).use_custom_shape_bone_size = True

        ctrl_list = [self.bones.ctrl.master]
        ControlLayersOption.SLIDER.assign_rig(self, ctrl_list)
    
    def rig_bones(self):

        """
        Rigs the bones in the rig.
        """
        
        bones = self.bones
        # Constrain the original bone.
        self.make_constraint(bones.org, 'COPY_TRANSFORMS', bones.ctrl.master, insert_index=0)
        # Constraints for the slider
        x = 1 * self.range
        y = 1 * self.range
        x_neg = -1 * self.range
        y_neg = -1 * self.range
        if self.clamp_up_down == 'DOWN':
            y = 0
        elif self.clamp_up_down == 'UP':
            y_neg = 0
        if not self.is_large():
            # clamp to 0 if not negative
            min_limit = (0, y_neg, 0, 0)
            max_limit = (0, y, 0)
        else:
            min_limit = (x_neg, y_neg, 0)
            max_limit = (x, y, 0)
        make_constraint(
            self.get_bone(bones.ctrl.master), 'LIMIT_LOCATION', 
            space='LOCAL', use_transform_limit=True, 
            min_xyz=min_limit,
            max_xyz=max_limit
        )
        make_constraint(
            self.get_bone(bones.ctrl.panel), 'LIMIT_LOCATION', 
            space='LOCAL', use_transform_limit=True, 
            min_xyz=(0,0,0),
            max_xyz=(0,0,0)
        )
    
    def is_large(self):
      
      """
      Checks if the slider type is LARGE.

      Returns:
          True if the slider type is LARGE, False otherwise.
      """

      return 'LARGE' in self.slider_type
    
    def generate_widgets(self):

        """
        Generates the widgets for the rig.
        """

        bones = self.bones
        params = self.params
        typology = params.slider_type
        offset = (0, 0, 0)
        bone = self.get_bone(bones.ctrl.master)
        title = bone.name if '@name' in self.custom_title else self.custom_title

        # Create control widget:
        box_wgt = createBoxWidget(rig=self.obj, bone_name=bones.ctrl.panel, design=typology, clp=self.clamp_up_down, txt=title, minimal=self.minimal_design, fill=self.fill_pan, bone_transform_name=None)
        ctrl_wgt = createControlWidget(rig=self.obj, bone_name=bones.ctrl.master, fill_it=self.fill_slider, off=self.fill_pan, bone_transform_name=None)
        
        # fixBoxWidget(box_wgt, design=typology, clp=self.clamp_up_down, txt=title, minimal=self.minimal_design, fill=self.fill_pan)
        # fixControlWidget(ctrl_wgt, fill_it=self.fill_slider, off=self.fill_pan)
        
        bpy.context.view_layer.objects.active = self.obj   

    @classmethod
    def add_parameters(cls, params):

        """
        Adds the parameters of this rig type to the RigifyParameters PropertyGroup.

        Args:
            params: The RigifyParameters PropertyGroup.
        """

        super().add_parameters(params)
        ControlLayersOption.SLIDER = ControlLayersOption('slider', description="Layers for the Slider controls to be on")

        params.slider_type = bpy.props.EnumProperty(name="Type", items=(('SMALL', "Small", "Small Slider"), ('LARGE', "Large", "Large Slider")))

        params.clamp_up_down = bpy.props.EnumProperty(name="Clamp", items=(('NONE', "None", ""), ('UP', "Clamp Up", "Cut the up area"), ('DOWN', "Clamp Down", "Cut the down area")))
        params.custom_title = bpy.props.StringProperty(name="Title", default='')
        params.fill_slider = bpy.props.BoolProperty(name='Fill Slider', default=False)
        params.minimal_design = bpy.props.BoolProperty(name='Minimal Slider', default=False)
        params.fill_pan = bpy.props.BoolProperty(name='Fill PAN', default=False)

        ControlLayersOption.SLIDER.add_parameters(params)

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
        
        col.prop(params, "slider_type")
        col.prop(params, "minimal_design")
        col.prop(params, "clamp_up_down")
        col.prop(params, "custom_title")
        col.label(text="write @name to write the bone name.", icon='INFO')
        col.prop(params, "fill_slider")
        
        if not params.minimal_design:
            col.prop(params, "fill_pan")

        cls.add_relink_constraints_ui(layout, params)
        if params.relink_constraints:
            col = layout.column()
            col.label(text="'CTRL:...' constraints are moved to the control bone.", icon='INFO')

        ControlLayersOption.SLIDER.parameters_ui(layout, params)


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
    set_params(pbone, "slider_type", 'SMALL')
         
    set_params(pbone, "relink_constraints", False)
        
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