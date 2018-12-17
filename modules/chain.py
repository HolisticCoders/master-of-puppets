import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField


class Chain(RigModule):

    chain_length = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    def initialize(self,*args, **kwargs):
        joints = []
        for i in range(self.chain_length.get()):
            self._add_driving_joint()

    def update(self):
        self._update_chain_length()

    def build(self):
        pass

    def publish(self):
        pass

    def _add_driving_joint(self):
        """Add a new driving joint, child of the last one.
        """
        parent = None
        if self.driving_joints:
            parent = self.driving_joints[-1]
        return super(Chain, self)._add_driving_joint(parent=parent)

    def _update_chain_length(self):
        diff = self.chain_length.get() - len(self.driving_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self._add_driving_joint()
                cmds.setAttr(new_joint + '.translateX', 5)
        elif diff < 0:
            joints = self.driving_joints
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]

            cmds.delete(joints_to_delete)

exported_rig_modules = [Chain]
