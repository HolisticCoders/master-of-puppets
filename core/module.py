import maya.cmds as cmds
from icarus.core.icarusNode import IcarusNode
from icarus.core.fields import ObjectField

class RigModule(IcarusNode):

    # Joint of the rig skeleton under which the deform joints will be parented.
    parent_joint = ObjectField('parent_joint')

    # Joints of this module that will be part of the rig's skeleton.
    deform_joints = ObjectField('deform_joints', multi=True)

    def __init__(self, name, side='M', *args, **kwargs):
        self.name = name
        self.side = side
        self.rig = kwargs.get('rig', None)
        node_name = '_'.join([name, side, 'mod'])
        super(RigModule, self).__init__(node_name)

    def initialize(self):
        """Creation of all the needed placement nodes.

        This must at least include all the module's deformation joints.

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

        The end result should _always_ drive your module's deform joints
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
