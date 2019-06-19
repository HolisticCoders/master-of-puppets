import maya.cmds as cmds

from mop.modules.leaf import Leaf
from mop.core.fields import IntField, ObjectField, BoolField
import mop.dag


class Twist(Leaf):

    twist_driver = ObjectField(
        displayable=True,
        editable=True,
        tooltip="Node used to derive the twist value from.",
    )

    reverse = BoolField(
        defaultValue=False,
        displayable=True,
        editable=True,
        gui_order=99,
        tooltip="If true, the higher the joint index, the less the joint will rotate.",
    )

    counter_twist = BoolField(
        defaultValue=False,
        displayable=True,
        editable=True,
        gui_order=99,
        tooltip="If true, the joints will get rotated in the opposite direction to the twist",
    )

    def build(self):
        twist_driver = self.twist_driver.get()
        twist_driver_parent = cmds.listRelatives(self.twist_driver.get(), parent=True)[
            0
        ]

        mult_mat = self.add_node('multMatrix', description='relative_space')
        decomp_mat = self.add_node('decomposeMatrix')
        quat_to_euler = self.add_node('quatToEuler')

        cmds.connectAttr(twist_driver + '.matrix', mult_mat + '.matrixIn[0]')
        cmds.setAttr(
            mult_mat + '.matrixIn[1]',
            cmds.getAttr(twist_driver + '.inverseMatrix'),
            type='matrix',
        )
        cmds.connectAttr(mult_mat + '.matrixSum', decomp_mat + '.inputMatrix')
        cmds.connectAttr(decomp_mat + '.outputQuatX', quat_to_euler + '.inputQuatX')
        cmds.connectAttr(decomp_mat + '.outputQuatW', quat_to_euler + '.inputQuatW')

        deform_joints = self.deform_joints.get()
        if not self.reverse.get():
            deform_joints.reverse()
        factor = 1.0 / self.joint_count.get()

        for i, joint in enumerate(deform_joints):
            current_factor = (i + 1) * factor
            current_factor_reverse = 1 - current_factor
            if self.counter_twist.get():
                current_factor *= -1
                current_factor_reverse *= -1

            metadata = mop.metadata.metadata_from_name(joint)
            anim_blend = self.add_node(
                'animBlendNodeAdditiveRotation',
                role='twistAmount',
                object_id=metadata['id'],
            )
            cmds.setAttr(anim_blend + '.weightA', current_factor)
            cmds.setAttr(anim_blend + '.weightB', current_factor_reverse)
            cmds.connectAttr(quat_to_euler + '.outputRotate', anim_blend + '.inputA')
            cmds.connectAttr(anim_blend + '.output', joint + '.rotate')


exported_rig_modules = [Twist]

