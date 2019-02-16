import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectField
import icarus.metadata
import icarus.dag
import icarus.attributes


class Corrective(RigModule):

    joint_count = IntField(
        displayable=True,
        editable=True,
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    vector_base = ObjectField() 
    vector_base_loc = ObjectField()
    vector_tip_loc = ObjectField()
    orig_pose_vector_tip_loc = ObjectField()

    def initialize(self):
        super(Corrective, self).initialize()
        for i in xrange(self.joint_count.get()):
            self._add_deform_joint()

    def update(self):
        super(Corrective, self).update()
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

    def build(self):
        self.vector_base.set(self.parent_joint.get())
        self.create_locators()
        value_range = self._build_angle_reader()
        for joint in self.driving_joints:
            ctl = self._add_control(joint)
            condition_nodes = []
            metadata = icarus.metadata.metadata_from_name(joint)
            for angleAxis in 'YZ':
                positive_offset = self.add_node(
                    'multiplyDivide',
                    role='mult',
                    description='positive_offset' + '_' + angleAxis,
                    object_id=metadata['id']
                )
                negative_offset = self.add_node(
                    'multiplyDivide',
                    role='mult',
                    description='negative_offset' + '_' + angleAxis,
                    object_id=metadata['id']
                )
                value_opposite = self.add_node(
                    'multDoubleLinear',
                    role='mult',
                    description='value_opposite' + '_' + angleAxis,
                    object_id=metadata['id']
                )
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
                condition = self.add_node(
                    'condition',
                    description=angleAxis,
                    object_id=metadata['id']
                )
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
            affected_by_cond = self.add_node(
                'condition',
                description='affected_by',
                object_id=metadata['id']
            )
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
        locator_space_group = self.add_node(
            'transform',
            role='vectorsLocalSpace'
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

        vector_base = cmds.listRelatives(
            self.add_node(
                'locator',
                description='vector_base'
            ),
            parent=True
        )[0]
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

        vector_tip = cmds.listRelatives(
            self.add_node(
                'locator',
                description='vector_tip'
            ),
            parent=True
        )[0]
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

        orig_pose_vector_tip = cmds.listRelatives(
            self.add_node(
                'locator',
                description='orig_pose_vector_tip'
            ),
            parent=True
        )[0]
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
        source_vector = self.add_node(
            'plusMinusAverage',
            role='vector',
            description='source'
        )
        cmds.setAttr(source_vector + '.operation', 2)
        target_vector = self.add_node(
            'plusMinusAverage',
            role='vector',
            description='target'
        )
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
        angle_between = self.add_node('angleBetween')
        cmds.connectAttr(
            source_vector + '.output3D',
            angle_between + '.vector1',
        )
        cmds.connectAttr(
            target_vector + '.output3D',
            angle_between + '.vector2',
        )

        self.node_mult = self.add_node(
            'multiplyDivide',
            role='mult',
            description='angle_times_axis'
        )
        cmds.connectAttr(
            angle_between + '.axis',
            self.node_mult + '.input1',
        )
        for axis in 'XYZ':
            cmds.connectAttr(
                angle_between + '.angle',
                self.node_mult + '.input2' + axis,
            )
        m1_to_p1_range = self.add_node(
            'multiplyDivide',
            role='mult',
            description='m1_to_p1_range'
        )
        cmds.setAttr(m1_to_p1_range + '.operation', 2)  # 2 is division
        cmds.connectAttr(
            self.node_mult + '.output',
            m1_to_p1_range + '.input1',
        )
        for axis in 'XYZ':
            cmds.setAttr(
                m1_to_p1_range + '.input2' + axis,
                180
            )
        return m1_to_p1_range

    def _add_control(self, joint):
        ctl, parent_group = self.add_control(joint)

        icarus.dag.snap_first_to_last(parent_group, joint)
        cmds.parent(parent_group, self.controls_group.get())

        offset_group = icarus.dag.add_parent_group(ctl, 'offset')
        icarus.dag.matrix_constraint(ctl, joint)

        icarus.attributes.create_persistent_attribute(
            ctl,
            self.node_name,
            ln='affectedBy',
            attributeType='enum',
            enumName='Y:Z:',
            keyable=True
        )

        # this attributes are there to ease the setup of the corrective for the rigger
        cmds.addAttr(
            ctl,
            longName='angle',
            attributeType='double',
        )
        cmds.setAttr(ctl + '.angle', channelBox=True)
        cmds.connectAttr(
            self.node_mult + '.input2X',
            ctl + '.angle'
        )
        cmds.addAttr(
            ctl,
            longName='xValue',
            attributeType='double',
        )
        cmds.setAttr(ctl + '.xValue', channelBox=True)
        cmds.connectAttr(
            self.node_mult + '.input1X',
            ctl + '.xValue'
        )
        cmds.addAttr(
            ctl,
            longName='yValue',
            attributeType='double',
        )
        cmds.setAttr(ctl + '.yValue', channelBox=True)
        cmds.connectAttr(
            self.node_mult + '.input1Y',
            ctl + '.yValue'
        )
        cmds.addAttr(
            ctl,
            longName='zValue',
            attributeType='double',
        )
        cmds.setAttr(ctl + '.zValue', channelBox=True)
        cmds.connectAttr(
            self.node_mult + '.input1Z',
            ctl + '.zValue'
        )

        for axis in 'XYZ':
            for transform in ['translate', 'rotate', 'scale']:
                cmds.setAttr(ctl + '.' + transform + axis, lock=True)
            icarus.attributes.create_persistent_attribute(
                ctl,
                self.node_name,
                ln='offset' + 'Positive' + axis,
                attributeType='long',
                keyable=True
            )
            icarus.attributes.create_persistent_attribute(
                ctl,
                self.node_name,
                ln='offset' + 'Negative' + axis,
                attributeType='long',
                keyable=True
            )

        return ctl

    def update_parent_joint(self):
        """Reparent the joints to the proper parent_joint if needed."""
        super(Corrective, self).update_parent_joint()
        for joint in self.deform_joints.get():
            expected_parent = self.parent_joint.get()
            actual_parent = cmds.listRelatives(joint, parent=True)[0]

            if expected_parent != actual_parent:
                cmds.parent(joint, expected_parent)


exported_rig_modules = [Corrective]

