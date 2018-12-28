import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectField
import icarus.dag


class Corrective(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    vector_base = ObjectField()  # should be provided by the user
    vector_tip = ObjectField()  # should be provided by the user

    vector_base_loc = ObjectField()
    vector_tip_loc = ObjectField()
    orig_pose_vector_tip_loc = ObjectField()

    def initialize(self):
        for i in xrange(self.joint_count.get()):
            self._add_deform_joint()
        self.vector_base.set(self.parent_joint.get())

    def update(self):
        deform_joints = self.deform_joints_list.get()
        if deform_joints is None:
            deform_joints = []

        diff = self.joint_count.get() - len(deform_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self._add_deform_joint()
                deform_joints.append(new_joint)
        elif diff < 0:
            joints = deform_joints
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]
            deform_joints = joints_to_keep
            cmds.delete(joints_to_delete)
        self.deform_joints_list.set(deform_joints)

    def build(self):
        self.create_locators()
        node_mult_angle = self._build_angle_reader()
        for joint in self.driving_joints:
            ctl = self._add_control(joint, name=joint + '_ctl')

    def create_locators(self):
        vector_base = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        vector_base = cmds.rename(
            vector_base,
            self.vector_base.get() + '_vectorBase'
        )
        cmds.parent(vector_base, self.extras_group.get())
        icarus.dag.snap_first_to_last(
            vector_base,
            self.vector_base.get()
        )
        icarus.dag.matrix_constraint(self.vector_base.get(), vector_base)
        self.vector_base_loc.set(vector_base)

        vector_tip = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        vector_tip = cmds.rename(
            vector_tip,
            self.vector_base.get() + '_vectorTip'
        )
        cmds.parent(vector_tip, self.extras_group.get())
        icarus.dag.snap_first_to_last(
            vector_tip,
            self.vector_tip.get()
        )
        icarus.dag.matrix_constraint(self.vector_tip.get(), vector_tip)
        self.vector_tip_loc.set(vector_tip)

        orig_pose_vector_tip = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        orig_pose_vector_tip = cmds.rename(
            orig_pose_vector_tip,
            self.vector_base.get() + '_vectorTipOrig'
        )
        cmds.parent(orig_pose_vector_tip, self.extras_group.get())
        icarus.dag.snap_first_to_last(
            orig_pose_vector_tip,
            self.vector_tip.get()
        )
        self.orig_pose_vector_tip_loc.set(orig_pose_vector_tip)

    def _build_angle_reader(self):
        # get the two vectors
        source_vector = cmds.createNode('plusMinusAverage')
        cmds.setAttr(source_vector + '.operation', 2)
        target_vector = cmds.createNode('plusMinusAverage')
        cmds.setAttr(target_vector + '.operation', 2)
        cmds.connectAttr(
            self.vector_tip_loc.get() + '.translate',
            source_vector + '.input3D[0]'
        )
        cmds.connectAttr(
            self.vector_base_loc.get() + '.translate',
            source_vector + '.input3D[1]'
        )
        cmds.connectAttr(
            self.orig_pose_vector_tip_loc.get() + '.translate',
            target_vector + '.input3D[0]'
        )
        cmds.connectAttr(
            self.vector_base_loc.get() + '.translate',
            target_vector + '.input3D[1]'
        )

        # get the angle between the two vectors
        angle_between = cmds.createNode('angleBetween')
        cmds.connectAttr(
            source_vector + '.output3D',
            angle_between + '.vector1',
        )
        cmds.connectAttr(
            target_vector + '.output3D',
            angle_between + '.vector2',
        )

        # # the axis angle value of the angleBetween node don't evaluate
        # # in realtime
        # # pipe the angleBetween euler angles to some quaternion stuff
        # # to get realtime axis angle.
        # euler_to_quat = cmds.createNode('eulerToQuat')
        # quat_to_axis_angle = cmds.createNode('quatToAxisAngle')
        # cmds.connectAttr(
        #     angle_between + '.euler',
        #     euler_to_quat + '.inputRotate',
        # )
        # cmds.connectAttr(
        #     euler_to_quat + '.outputQuat',
        #     quat_to_axis_angle + '.inputQuat',
        # )
        node_mult = cmds.createNode('multiplyDivide')
        cmds.connectAttr(
            angle_between + '.axis',
            node_mult + '.input1',
        )
        for axis in 'XYZ':
            cmds.connectAttr(
                angle_between + '.angle',
                node_mult + '.input2' + axis,
            )
        return node_mult

    def _add_control(self, joint, name):
        ctl = cmds.circle(name=name)[0]

        icarus.dag.snap_first_to_last(ctl, joint)
        cmds.parent(ctl, self.controls_group.get())

        offset_group = icarus.dag.add_parent_group(ctl, 'offset')
        icarus.dag.add_parent_group(ctl, 'buffer')
        icarus.dag.matrix_constraint(ctl, joint)

        cmds.addAttr(
            ctl,
            ln='activeValue',
            attributeType='double',
            keyable=True
        )

        for axis in 'XYZ':
            for transform in ['translate', 'rotate', 'scale']:
                cmds.setAttr(ctl + '.' + transform + axis, lock=True)

            if axis == 'X':  # there's no angle difference when twisting
                continue

            cmds.addAttr(
                ctl,
                ln='offset' + 'Positive' + axis,
                attributeType='long',
                keyable=True
            )
            cmds.addAttr(
                ctl,
                ln='offset' + 'Negative' + axis,
                attributeType='long',
                keyable=True
            )

        return ctl

exported_rig_modules = [Corrective]
