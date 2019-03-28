import maya.api.OpenMaya as om2
import maya.cmds as cmds
import maya.mel as mel

from mop.modules.abstract.fkikchain import FkIkChain
import mop.metadata

from mop.core.fields import (
    StringField,
    ObjectListField,
    ObjectField,
)


class FkIkSpringChain(FkIkChain):

    def initialize(self):
        super(FkIkSpringChain, self).initialize()
        # make sure the spring solver is loaded
        mel.eval('ikSpringSolver') 

    def _create_ik_handle(self):
        ik_chain = self.chain_b.get()
        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],
            endEffector=ik_chain[-1],
            solver='ikSpringSolver'
        )
        self.ik_handle.set(ik_handle)
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(self.ik_pv_ctl.get(), ik_handle)
        mop.dag.matrix_constraint(
            self.ik_end_ctl.get(),
            ik_handle,
            maintain_offset=True
        )

    def _place_pole_vector(self):
        buffer_group = cmds.listRelatives(self.ik_pv_ctl.get(), parent=True)[0]
        ik_chain = self.chain_b.get()
        start_pos = cmds.xform(
            ik_chain[0],
            query=True,
            worldSpace=True,
            translation=True
        )
        mid_pos = cmds.xform(
            ik_chain[1],
            query=True,
            worldSpace=True,
            translation=True
        )
        end_pos = cmds.xform(
            ik_chain[-1],
            query=True,
            worldSpace=True,
            translation=True
        )

        start_vec = om2.MVector(*start_pos)
        mid_vec = om2.MVector(*mid_pos)
        end_vec = om2.MVector(*end_pos)

        start_end_vec = end_vec - start_vec
        start_mid_vec = mid_vec - start_vec

        dot_product = start_mid_vec * start_end_vec
        proj = float(dot_product) / float(start_end_vec.length())
        start_end_vec_norm = start_end_vec.normal()
        projection_vec = start_end_vec_norm * proj

        pole_vec = start_mid_vec - projection_vec
        pole_vec *= 10
        pv_control_vec = pole_vec + mid_vec
        cmds.xform(buffer_group, worldSpace=1, translation=pv_control_vec)


exported_rig_modules = [FkIkSpringChain]
