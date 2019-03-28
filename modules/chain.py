import math

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.modules.abstract.abstractchain import AbstractChain
from icarus.core.fields import IntField, ObjectListField
import icarus.dag


class Chain(AbstractChain):

    offset_control_count = IntField(
        defaultValue=0,
        hasMinValue=True,
        minValue=0,
        displayable=True,
        editable=True,
        tooltip="The number of joints for the chain."
    )

    def build(self):
        fk_parent = self.controls_group.get()
        for fk_id, joint in enumerate(self.driving_joints):
            # Add the fk control
            fk_ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, fk_parent)

            fk_parent = fk_ctl
            constrain_ctl = fk_ctl

            # create the offset controls
            for i in range(self.offset_control_count.get()):
                offset_ctl, parent_group = self.add_control(
                    joint,
                    object_id=i,
                    description='offset_{}'.format(str(fk_id).zfill(3)),
                    shape_type='sphere'
                )
                cmds.parent(parent_group, constrain_ctl)
                constrain_ctl = offset_ctl

            icarus.dag.matrix_constraint(constrain_ctl, joint)


exported_rig_modules = [Chain]
