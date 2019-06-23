import logging
import maya.cmds as cmds

from mop.core.module import RigModule
import mop.dag


logger = logging.getLogger(__name__)


class Root(RigModule):
    def create_guide_nodes(self):
        """The root module doesn't need guide joints."""
        pass

    def constraint_deforms_to_guides(self):
        pass

    def create_deform_joints(self):
        if len(self.deform_joints) == 0:
            joint = self.add_deform_joint()

    def build(self):
        global_ctl, global_buffer = self.add_control(self.deform_joints[0])
        mop.dag.matrix_constraint(global_ctl, self.deform_joints[0])
        cmds.parent(global_buffer, self.controls_group.get())


exported_rig_modules = [Root]
