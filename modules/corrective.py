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

    vector_base = ObjectField()
    vector_tip = ObjectField()

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
        for joint in self.driving_joints:
            ctl = self._add_control(joint, name=joint + '_ctl')
            target_vector_tip = cmds.listRelatives(cmds.createNode(
                'locator',
            ), parent=True)[0]
            target_vector_tip = cmds.rename(
                target_vector_tip,
                joint + '_targetPose'
            )
            cmds.parent(target_vector_tip, self.extras_group.get())
            target_vector_tip_group = icarus.dag.add_parent_group(
                target_vector_tip
            )
            icarus.dag.matrix_constraint(
                cmds.listRelatives(self.vector_base.get(), parent=True)[0],
                target_vector_tip_group
            )
            # get the world coordinates of the transform
            # to create vectors later
            decompose_vector_base = cmds.createNode('decomposeMatrix')
            decompose_vector_tip = cmds.createNode('decomposeMatrix')
            decompose_vector_target_tip = cmds.createNode('decomposeMatrix')
            cmds.connectAttr(
                self.vector_base.get() + '.worldMatrix',
                decompose_vector_base + '.inputMatrix'
            )
            cmds.connectAttr(
                self.vector_tip.get() + '.worldMatrix',
                decompose_vector_tip + '.inputMatrix'
            )
            cmds.connectAttr(
                target_vector_tip + '.worldMatrix',
                decompose_vector_target_tip + '.inputMatrix'
            )

            # get the two vectors
            source_vector = cmds.createNode('plusMinusAverage')
            cmds.setAttr(source_vector + '.operation', 2)
            target_vector = cmds.createNode('plusMinusAverage')
            cmds.setAttr(target_vector + '.operation', 2)
            cmds.connectAttr(
                decompose_vector_tip + '.outputTranslate',
                source_vector + '.input3D[0]'
            )
            cmds.connectAttr(
                decompose_vector_base + '.outputTranslate',
                source_vector + '.input3D[1]'
            )
            cmds.connectAttr(
                decompose_vector_target_tip + '.outputTranslate',
                target_vector + '.input3D[0]'
            )
            cmds.connectAttr(
                decompose_vector_base + '.outputTranslate',
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

            # remap the output angle to a 0-1 value
            # if it sits inside the cone angle
            half_cone_angle = cmds.createNode('multDoubleLinear')
            cmds.connectAttr(
                ctl + '.coneAngle',
                half_cone_angle + '.input1',
            )
            cmds.setAttr(half_cone_angle + '.input2', 0.5)
            remap_value = cmds.createNode('remapValue')
            cmds.connectAttr(
                half_cone_angle + '.output',
                remap_value + '.inputMax',
            )
            cmds.connectAttr(
                angle_between + '.axisAngle.angle',
                remap_value + '.inputValue',
            )
            cmds.setAttr(remap_value + '.outputMin', 1)
            cmds.setAttr(remap_value + '.outputMax', 0)
            cmds.connectAttr(
                remap_value + '.outValue',
                ctl + '.activeValue',
            )

            # compute the offset when the pose is reached
            corrective_offset = cmds.createNode('multiplyDivide')
            offset_group = cmds.listRelatives(ctl, parent=True)[0]
            for axis in 'XYZ':
                cmds.connectAttr(
                    ctl + '.offset' + axis,
                    corrective_offset + '.input1' + axis,
                )
                cmds.connectAttr(
                    remap_value + '.outValue',
                    corrective_offset + '.input2' + axis,
                )
                cmds.connectAttr(
                    corrective_offset + '.output' + axis,
                    offset_group + '.translate' + axis,
                )

    def _add_control(self, joint, name):
        ctl = cmds.circle(name=name)[0]

        icarus.dag.snap_first_to_last(ctl, joint)
        cmds.parent(ctl, self.controls_group.get())

        offset_group = icarus.dag.add_parent_group(ctl, 'offset')
        icarus.dag.add_parent_group(ctl, 'buffer')
        icarus.dag.matrix_constraint(ctl, joint)

        for axis in 'XYZ':
            for transform in ['translate', 'rotate', 'scale']:
                cmds.setAttr(ctl + '.' + transform + axis, lock=True)
            cmds.addAttr(
                ctl,
                ln='offset' + axis,
                attributeType='long',
                keyable=True
            )
        cmds.addAttr(
            ctl,
            ln='coneAngle',
            attributeType='long',
            keyable=True,
        )
        cmds.setAttr(ctl + '.coneAngle', 90)
        cmds.addAttr(
            ctl,
            ln='activeValue',
            attributeType='double',
            keyable=True
        )
        return ctl

exported_rig_modules = [Corrective]
