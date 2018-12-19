import maya.cmds as cmds

from icarus.core.module import RigModule
import icarus.metadata

class Root(RigModule):

    def initialize(self):
        self._add_deform_joint()

    def update(self):
        pass

    def build(self):
        pass

    def publish(self):
        pass

exported_rig_modules = [Root]
