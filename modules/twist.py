import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectField, BoolField
import icarus.dag

class Twist(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        displayable=True,
        editable=True,
        gui_order=-1,
        tooltip="The number of twist joints."
    )

    twist_driver = ObjectField(
        displayable=True,
        editable=True,
        tooltip="Node used to derive the twist value from."
    )

    reverse = BoolField(
        defaultValue=False,
        displayable=True,
        editable=True,
        gui_order=99,
        tooltip="If true, the higher the joint index, the less the joint will rotate."
    )

    counter_twist = BoolField(
        defaultValue=False,
        displayable=True,
        editable=True,
        gui_order=99,
        tooltip="If true, the joints will get rotated in the opposite direction to the twist"
    )

    def update(self):
        super(Twist, self).update()
        diff = self.joint_count.get() - len(self.deform_joints)
        if diff > 0:
            for index in range(diff):
                self._add_deform_joint()
        elif diff < 0:
            joints = self.deform_joints.get()
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]

            for module in self.rig.rig_modules:
                if module.parent_joint.get() in joints_to_delete:
                    if joints_to_keep:
                        new_parent_joint = joints_to_keep[-1]
                    else:
                        new_parent_joint = self.parent_joint.get()
                    module.parent_joint.set(new_parent_joint)
                    module.update()

            cmds.delete(joints_to_delete)

    def update_parent_joint(self):
        """Reparent the joints to the proper parent_joint if needed."""
        super(Twist, self).update_parent_joint()
        for joint in self.deform_joints.get():
            expected_parent = self.parent_joint.get()
            actual_parent = cmds.listRelatives(joint, parent=True)[0]

            if expected_parent != actual_parent:
                cmds.parent(joint, expected_parent)

    def build(self):
        twist_driver = self.twist_driver.get()
        twist_driver_parent = cmds.listRelatives(
            self.twist_driver.get(),
            parent=True
        )[0]

        mult_mat = self.add_node(
            'multMatrix',
            description='relative_space',
        )
        decomp_mat = self.add_node('decomposeMatrix')
        quat_to_euler = self.add_node('quatToEuler')

        cmds.connectAttr(
            twist_driver + '.worldMatrix[0]',
            mult_mat + '.matrixIn[0]'
        )
        cmds.connectAttr(
            twist_driver_parent + '.worldInverseMatrix[0]',
            mult_mat + '.matrixIn[1]'
        )
        cmds.connectAttr(
            mult_mat + '.matrixSum',
            decomp_mat + '.inputMatrix',
        )
        cmds.connectAttr(
            decomp_mat + '.outputQuatX',
            quat_to_euler + '.inputQuatX',
        )
        cmds.connectAttr(
            decomp_mat + '.outputQuatW',
            quat_to_euler + '.inputQuatW',
        )

        driving_joints = self.driving_joints
        if not self.reverse.get():
            driving_joints.reverse()
        factor = 1.0 / self.joint_count.get()

        for i, joint in enumerate(driving_joints):
            current_factor = (i + 1) * factor
            current_factor_reverse = 1 - current_factor
            if self.counter_twist.get():
                current_factor *= -1
                current_factor_reverse *= -1

            metadata = icarus.metadata.metadata_from_name(joint)
            anim_blend = self.add_node(
                'animBlendNodeAdditiveRotation',
                role='twistAmount',
                object_id=metadata['id'],
            )
            cmds.setAttr(
                anim_blend + '.weightA',
                current_factor
            )
            cmds.setAttr(
                anim_blend + '.weightB',
                current_factor_reverse
            )
            cmds.connectAttr(
                quat_to_euler + '.outputRotate',
                anim_blend + '.inputA',
            )
            cmds.connectAttr(
                anim_blend + '.output',
                joint + '.rotate'
            )



exported_rig_modules = [Twist]

