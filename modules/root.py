import maya.cmds as cmds

from icarus.core.module import RigModule


class Root(RigModule):

    def initialize(self):
        self.deform_joints.set([cmds.createNode('joint', name='root')])

    def update(self):
        pass

    def build(self):
        pass

    def publish(self):
        pass

exported_rig_modules = [Root]
