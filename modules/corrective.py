import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectField
import icarus.dag


class Corrective(RigModule):

    joint_count = IntField(
        displayable=True,
        editable=True,
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    vector_base = ObjectField(
        displayable=True,
        editable=True,
    ) 

    vector_base_loc = ObjectField()
    vector_tip_loc = ObjectField()
    orig_pose_vector_tip_loc = ObjectField()

    def initialize(self):
        for i in xrange(self.joint_count.get()):
            self._add_deform_joint()
        self.vector_base.set(self.parent_joint.get())

    def update(self):
        super(Corrective, self).update()
        deform_joints = self.deform_joints.get()
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
        self.deform_joints.set(deform_joints)

    def build(self):
        self.create_locators()
        value_range = self._build_angle_reader()
        for joint in self.driving_joints:
            ctl = self._add_control(joint, name=joint + '_ctl')
            condition_nodes = []
            for angleAxis in 'YZ':
                positive_offset = cmds.createNode('multiplyDivide')
                negative_offset = cmds.createNode('multiplyDivide')
                value_opposite = cmds.createNode('multDoubleLinear')
                cmds.connectAttr(
                    value_range + '.output' + angleAxis,
                    value_opposite + '.input1'
                )
                cmds.setAttr(value_opposite + '.input2', -1)
                for axis in 'XYZ':
                    cmds.connectAttr(
                        value_range + '.output' + angleAxis,
                        positive_offset + '.input1' + axis
                    )
                    cmds.connectAttr(
                        ctl + '.offsetPositive' + axis,
                        positive_offset + '.input2' + axis
                    )
                    cmds.connectAttr(
                        value_opposite + '.output',
                        negative_offset + '.input1' + axis
                    )
                    cmds.connectAttr(
                        ctl + '.offsetNegative' + axis,
                        negative_offset + '.input2' + axis
                    )
                condition = cmds.createNode('condition')
                cmds.setAttr(condition + '.operation', 3)  # 3 is >=
                condition_nodes.append(condition)
                cmds.connectAttr(
                    value_range + '.output' + angleAxis,
                    condition + '.firstTerm'
                )
                cmds.connectAttr(
                    positive_offset + '.output',
                    condition + '.colorIfTrue'
                )
                cmds.connectAttr(
                    negative_offset + '.output',
                    condition + '.colorIfFalse'
                )
            affected_by_cond = cmds.createNode('condition')
            cmds.connectAttr(
                ctl + '.affectedBy',
                affected_by_cond + '.firstTerm'
            )
            cmds.connectAttr(
                condition_nodes[0] + '.outColor',
                affected_by_cond + '.colorIfTrue'
            )
            cmds.connectAttr(
                condition_nodes[1] + '.outColor',
                affected_by_cond + '.colorIfFalse'
            )
            cmds.connectAttr(
                affected_by_cond + '.outColor',
                ctl + '.translate',
            )

    def create_locators(self):
        locator_space_group = cmds.createNode('transform')
        locator_space_group = cmds.rename(
            locator_space_group,
            icarus.metadata.name_from_metadata(
                self.name.get(),
                self.side.get(),
                'vectorsLocalSpace'
            )
        )
        cmds.parent(locator_space_group, self.extras_group.get())
        cmds.setAttr(locator_space_group + '.inheritsTransform', False)
        icarus.dag.snap_first_to_last(
            locator_space_group,
            self.vector_base.get()
        )
        cmds.pointConstraint(
            self.vector_base.get(),
            locator_space_group
        )

        vector_base = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        vector_base = cmds.rename(
            vector_base,
            self.vector_base.get() + '_vectorBase'
        )
        cmds.parent(vector_base, locator_space_group)
        icarus.dag.snap_first_to_last(
            vector_base,
            self.vector_base.get()
        )
        # icarus.dag.matrix_constraint(self.vector_base.get(), vector_base)
        cmds.parentConstraint(self.vector_base.get(), vector_base)
        self.vector_base_loc.set(vector_base)

        vector_tip = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        vector_tip = cmds.rename(
            vector_tip,
            self.vector_base.get() + '_vectorTip'
        )

        # give a magnitude to the vector
        cmds.parent(vector_tip, vector_base)
        icarus.dag.reset_node(vector_tip)
        cmds.setAttr(vector_tip + '.translateX', 1)

        cmds.parent(vector_tip, locator_space_group)
        cmds.parentConstraint(vector_base, vector_tip, maintainOffset=True)
        self.vector_tip_loc.set(vector_tip)

        orig_pose_vector_tip = cmds.listRelatives(cmds.createNode(
            'locator',
        ), parent=True)[0]
        orig_pose_vector_tip = cmds.rename(
            orig_pose_vector_tip,
            self.vector_base.get() + '_vectorTipOrig'
        )

        # give a magnitude to the vector
        cmds.parent(orig_pose_vector_tip, vector_base)
        icarus.dag.reset_node(orig_pose_vector_tip)
        cmds.setAttr(orig_pose_vector_tip + '.translateX', 1)

        cmds.parent(orig_pose_vector_tip, locator_space_group)
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
        m1_to_p1_range = cmds.createNode('multiplyDivide')
        cmds.setAttr(m1_to_p1_range + '.operation', 2)  # 2 is division
        cmds.connectAttr(
            node_mult + '.output',
            m1_to_p1_range + '.input1',
        )
        for axis in 'XYZ':
            cmds.setAttr(
                m1_to_p1_range + '.input2' + axis,
                180
            )
        return m1_to_p1_range

    def _add_control(self, joint, name):
        ctl = cmds.circle(name=name)[0]

        icarus.dag.snap_first_to_last(ctl, joint)
        cmds.parent(ctl, self.controls_group.get())

        offset_group = icarus.dag.add_parent_group(ctl, 'offset')
        icarus.dag.add_parent_group(ctl, 'buffer')
        icarus.dag.matrix_constraint(ctl, joint)

        icarus.metadata.create_persistent_attribute(
            ctl,
            self.node_name,
            ln='affectedBy',
            attributeType='enum',
            enumName='Y:Z:',
            keyable=True
        )

        for axis in 'XYZ':
            for transform in ['translate', 'rotate', 'scale']:
                cmds.setAttr(ctl + '.' + transform + axis, lock=True)
            icarus.metadata.create_persistent_attribute(
                ctl,
                self.node_name,
                ln='offset' + 'Positive' + axis,
                attributeType='long',
                keyable=True
            )
            icarus.metadata.create_persistent_attribute(
                ctl,
                self.node_name,
                ln='offset' + 'Negative' + axis,
                attributeType='long',
                keyable=True
            )

        return ctl


exported_rig_modules = [Corrective]

