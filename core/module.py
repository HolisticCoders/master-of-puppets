import maya.cmds as cmds
from icarus.core.icarusNode import IcarusNode
from icarus.core.fields import ObjectField, StringField, JSONField
import icarus.metadata
import icarus.dag

class RigModule(IcarusNode):

    name = StringField()
    side = StringField()
    module_type = StringField()

    # Joint of the rig skeleton under which the deform joints will be parented.
    parent_joint = ObjectField()

    # group holding all this module's controls
    controls_group = ObjectField()

    # list of all of this module's deform joints
    deform_joints_list = JSONField()

    # dict representing this module's deform joints hierarchy
    deform_joints_dict = JSONField()

    def __init__(self, name, side='M', parent_joint=None, rig=None):
        if cmds.objExists(name):
            self.node_name = name
        else:
            self.node_name = icarus.metadata.name_from_metadata(name, side, 'mod')
        super(RigModule, self).__init__(self.node_name)

        self.rig = rig

        if not self.is_initialized.get():
            self.name.set(name)
            self.side.set(side)
            self.module_type.set(self.__class__.__name__)

            if parent_joint:
                self.parent_joint.set(parent_joint)

            controls_group_name = icarus.metadata.name_from_metadata(
                name,
                side,
                'grp',
                object_description='controls'
            )
            self.controls_group.set(cmds.createNode(
                'transform',
                name=controls_group_name,
                parent=self.node_name
            ))


            self.initialize()
            self.is_initialized.set(True)

    def initialize(self):
        """Creation of all the needed placement nodes.

        This must at least include all the module's driving joints.

        Will be called automatically when creating the module.
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def update(self):
        """Update the placement based on the module's fields.

        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def build(self):
        """Actual rigging of the module.

        The end result should _always_ drive your module's driving joints
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def publish(self):
        """Clean the rig for the animation.

        Nothing in there should change how the rig works.
        It's meant to hide some stuff that the rigger would need after the build
        maybe lock some attributes, set some default values, etc.
        You need to overwrite this method in your subclasses.
        """
        raise NotImplementedError

    def _add_deform_joint(self, name=None, parent=None):
        """Creates a new deform joint for this module.

        Args:
            name (str): name of the joint, in case you don't want the default one.
            parent (str): node under which the new joint will be parented
        """
        deform_joints = self.deform_joints_list.get()

        if deform_joints is None:
            deform_joints = []

        object_id=len(deform_joints)
        if name is not None:
            new_joint = name
        else:
            new_joint = icarus.metadata.name_from_metadata(
                self.name.get(),
                self.side.get(),
                'deform',
                object_id=object_id
            )
        cmds.createNode('joint', name=new_joint)

        if not parent:
            parent = self.parent_joint.get()
        if not parent:
            parent = self.rig.skeleton_group.get()

        cmds.parent(new_joint, parent)

        deform_joints.append(new_joint)
        self.deform_joints_list.set(
            deform_joints
        )

        tree = {}
        hierachy_parent = self.parent_joint.get()
        if not hierachy_parent:
            hierachy_parent = self.rig.skeleton_group.get()

        for joint in cmds.listRelatives(hierachy_parent):
            icarus.dag.hierarchy_to_dict(hierachy_parent, tree, deform_joints)
        self.deform_joints_dict.set(tree)
        return new_joint
