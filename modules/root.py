import maya.cmds as cmds

from icarus.core.module import RigModule
import icarus.metadata

class Root(RigModule):

    def initialize(self):
        self._add_deform_joint()

    def build(self):
        cmds.makeIdentity(self.deform_joints.get()[0], apply=True, rotate=True)

    def publish(self):
        pass

exported_rig_modules = [Root]
