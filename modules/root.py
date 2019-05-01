import logging
import maya.cmds as cmds

from mop.core.module import RigModule
import mop.dag


logger = logging.getLogger(__name__)


class Root(RigModule):

    def initialize(self):
        super(Root, self).initialize()
        self._add_deform_joint()

    def build(self):
        global_ctl, global_buffer = self.add_control(self.driving_joints[0])
        mop.dag.matrix_constraint(global_ctl, self.driving_joints[0])
        cmds.parent(global_buffer, self.controls_group.get())


exported_rig_modules = [Root]

