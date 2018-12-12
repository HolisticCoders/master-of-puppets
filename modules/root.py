import maya.cmds as cmds

from icarus.core.module import RigModule


class Root(RigModule):

    def initialize(self):
        self.deform_joints.set([cmds.createNode('joint', name='root')])

exported_rig_modules = [Root]
