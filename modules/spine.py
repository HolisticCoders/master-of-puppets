import maya.cmds as cmds

from mop.core.fields import IntField
from mop.modules.chain import Chain

import mop.dag
import mop.metadata


class Spine(Chain):

    joint_count = IntField(
        defaultValue=4,
        hasMinValue=True,
        minValue=4,
        hasMaxValue=True,
        displayable=True,
        editable=True,
        tooltip="The number of joints for the spine.\n" "This includes the pelvis",
    )

    def build(self):
        parent = self.controls_group.get()
        for i, joint in enumerate(self.deform_joints):
            fk_ctl, parent_group = self.add_control(joint, description="fk")
            cmds.parent(parent_group, parent)
            parent = fk_ctl
            if i == 0:
                # pelvis joint, setup the reverse pelvis behavior.
                # but first, rename the FK control to avoid conflicts later on.
                next_joint = self.deform_joints[i + 1]
                reverse_pelvis_ctl, reverse_pelvis_grp = self.add_control(
                    next_joint, description="reverse_pelvis", shape_type="cube"
                )
                cmds.parent(reverse_pelvis_grp, fk_ctl)

                pelvis_ctl, pelvis_grp = self.add_control(
                    joint, description="pelvis", shape_type="cube"
                )
                cmds.parent(pelvis_grp, reverse_pelvis_ctl)
                mop.dag.matrix_constraint(pelvis_ctl, joint)

            else:
                # spine joints, parent constraint the joint directly
                mop.dag.matrix_constraint(fk_ctl, joint)


exported_rig_modules = [Spine]
