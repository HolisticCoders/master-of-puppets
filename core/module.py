import maya.cmds as cmds
from icarus.core.icarusNode import IcarusNode
from icarus.core.fields import ObjectField
import icarus.utils

class RigModule(IcarusNode):

    # Joint of the rig skeleton under which the driving joints will be parented.
    parent_joint = ObjectField('parent_joint')

    # group holding all this module's driving joints
    driving_group = ObjectField('driving_group')


    def __init__(self, name, side='M', parent_joint=None, *args, **kwargs):
        self.node_name = icarus.utils.name_from_metadata(name, side, 'mod')
        super(RigModule, self).__init__(self.node_name)

        self.name = name
        self.side = side
        self.parent_joint = parent_joint
        self.rig = kwargs.get('rig', None)

        driving_group_name = icarus.utils.name_from_metadata(
            name,
            side,
            'grp',
            object_description='driving'
        )
        cmds.createNode('transform', name=driving_group_name, parent=self.node_name)
        self.driving_group.set(driving_group_name)

    @property
    def driving_joints(self):
        joints = cmds.listRelatives(self.driving_group.get(), type='joint', allDescendents=True)
        if joints is None:
            return []
        else:
            return list(reversed(joints)) # listRelative returns a reversed list.

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

    def _add_driving_joint(self, name=None, parent=None):
        """Creates a new driving joint for this module.

        Args:
            name (str): name of the joint, in case you don't want the default one.
            parent (str): node under which the new joint will be parented
        """
        object_id=len(self.driving_joints)
        if name is not None:
            new_joint = name
        else:
            new_joint = icarus.utils.name_from_metadata(
                self.name,
                self.side,
                'driver',
                object_id=object_id
            )
        cmds.createNode('joint', name=new_joint)

        if parent:
            cmds.parent(new_joint, parent)
        else:
            cmds.parent(new_joint, self.driving_group.get())
        return new_joint
