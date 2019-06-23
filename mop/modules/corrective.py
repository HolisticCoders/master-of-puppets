import maya.cmds as cmds
import mop.vendor.node_calculator.core as noca

from mop.modules.leaf import Leaf
from mop.core.fields import IntField, ObjectField
import mop.metadata
import mop.dag
import mop.attributes


class Corrective(Leaf):

    vector_base = ObjectField(
        displayable=True,
        editable=True,
        gui_order=1,  # make sure it's always on top
        tooltip="Base of the vector that is used to track the difference between the original pose and the current one.\n"
        "If left empty, this will automatically be set to the parent joint.",
    )
    vector_tip = ObjectField(
        displayable=True,
        editable=True,
        gui_order=2,  # make sure it's always on top
        tooltip="Tip of the vector that is used to track the difference between the original pose and the current one.\n"
        "If left empty, the vector used will be along the +X axis of the Vector Base.",
    )

    vector_base_loc = ObjectField()
    vector_tip_loc = ObjectField()
    orig_pose_vector_tip_loc = ObjectField()

    def build(self):
        if not self.vector_base.get():
            self.vector_base.set(self.parent_joint.get())

        self.create_locators()
        value_range = self._build_angle_reader()
        for joint in self.deform_joints:
            ctl = noca.Node(self._add_control(joint))
            condition_nodes = []
            metadata = mop.metadata.metadata_from_name(joint)
            for angle_axis in "YZ":
                axis_range = value_range.attr("output" + angle_axis)
                value_opposite = axis_range * -1
                positive_offset = value_range * [
                    ctl.offsetPositiveX,
                    ctl.offsetPositiveY,
                    ctl.offsetPositiveZ,
                ]
                negative_offset = value_opposite * [
                    ctl.offsetNegativeX,
                    ctl.offsetNegativeY,
                    ctl.offsetNegativeZ,
                ]
                condition = noca.Op.condition(
                    axis_range >= 0, positive_offset.output, negative_offset.output
                )
                condition_nodes.append(condition)
            ctl.translate = noca.Op.condition(
                ctl.affectedBy == 0,
                condition_nodes[0].outColor,
                condition_nodes[1].outColor,
            )

    def create_locators(self):
        locator_space_group = self.add_node("transform", role="vectorsLocalSpace")
        cmds.parent(locator_space_group, self.extras_group.get())
        cmds.setAttr(locator_space_group + ".inheritsTransform", False)
        mop.dag.snap_first_to_last(locator_space_group, self.vector_base.get())
        cmds.pointConstraint(self.vector_base.get(), locator_space_group)

        vector_base_loc = self.add_node("locator", description="vector_base")
        vector_base_loc = cmds.rename(
            vector_base_loc, self.vector_base.get() + "_vectorBase"
        )
        cmds.parent(vector_base_loc, locator_space_group)
        mop.dag.snap_first_to_last(vector_base_loc, self.vector_base.get())
        cmds.parentConstraint(self.vector_base.get(), vector_base_loc)
        self.vector_base_loc.set(vector_base_loc)

        vector_tip = self.add_node("locator", description="vector_tip")
        vector_tip = cmds.rename(vector_tip, self.vector_base.get() + "_vectorTip")

        # give a magnitude to the vector
        if self.vector_tip.get():
            cmds.parent(vector_tip, locator_space_group)
            mop.dag.snap_first_to_last(vector_tip, self.vector_tip.get())
            mop.dag.matrix_constraint(
                self.vector_tip.get(), vector_tip, maintain_offset=True
            )
        else:
            mop.dag.reset_node(vector_tip)
            cmds.setAttr(vector_tip + ".translateX", 1)
            cmds.parent(vector_tip, vector_base_loc)
            cmds.parent(vector_tip, locator_space_group)
            mop.dag.matrix_constraint(vector_base_loc, vector_tip, maintain_offset=True)
        self.vector_tip_loc.set(vector_tip)

        orig_pose_vector_tip = self.add_node(
            "locator", description="orig_pose_vector_tip"
        )
        orig_pose_vector_tip = cmds.rename(
            orig_pose_vector_tip, self.vector_base.get() + "_vectorTipOrig"
        )

        # give a magnitude to the vector
        cmds.parent(orig_pose_vector_tip, vector_base_loc)
        mop.dag.reset_node(orig_pose_vector_tip)
        cmds.setAttr(orig_pose_vector_tip + ".translateX", 1)

        cmds.parent(orig_pose_vector_tip, locator_space_group)
        self.orig_pose_vector_tip_loc.set(orig_pose_vector_tip)

    def _build_angle_reader(self):
        # get the two vectors
        vector_tip = noca.Node(self.vector_tip_loc.get())
        vector_base = noca.Node(self.vector_base_loc.get())
        orig_vector_tip = noca.Node(self.orig_pose_vector_tip_loc.get())

        source_vector = vector_tip.translate - vector_base.translate
        target_vector = orig_vector_tip.translate - vector_base.translate

        angle_between = noca.Op.angle_between(source_vector, target_vector)

        angle_result = angle_between.axis * angle_between.angle
        self.angle_result_node = angle_result.node

        minus_one_to_one_range = angle_result / 180

        return minus_one_to_one_range

    def _add_control(self, joint):
        ctl, parent_group = self.add_control(joint)

        mop.dag.snap_first_to_last(parent_group, joint)
        cmds.parent(parent_group, self.controls_group.get())

        offset_group = mop.dag.add_parent_group(ctl, "offset")
        mop.dag.matrix_constraint(ctl, joint)

        mop.attributes.create_persistent_attribute(
            ctl,
            self.node_name,
            ln="affectedBy",
            attributeType="enum",
            enumName="Y:Z:",
            keyable=True,
        )

        # this attributes are there to ease the setup of the corrective for the rigger
        cmds.addAttr(ctl, longName="angle", attributeType="double")
        cmds.setAttr(ctl + ".angle", channelBox=True)
        cmds.connectAttr(self.angle_result_node + ".input2X", ctl + ".angle")
        cmds.addAttr(ctl, longName="xValue", attributeType="double")
        cmds.setAttr(ctl + ".xValue", channelBox=True)
        cmds.connectAttr(self.angle_result_node + ".input1X", ctl + ".xValue")
        cmds.addAttr(ctl, longName="yValue", attributeType="double")
        cmds.setAttr(ctl + ".yValue", channelBox=True)
        cmds.connectAttr(self.angle_result_node + ".input1Y", ctl + ".yValue")
        cmds.addAttr(ctl, longName="zValue", attributeType="double")
        cmds.setAttr(ctl + ".zValue", channelBox=True)
        cmds.connectAttr(self.angle_result_node + ".input1Z", ctl + ".zValue")

        for axis in "XYZ":
            for transform in ["translate", "rotate", "scale"]:
                cmds.setAttr(ctl + "." + transform + axis, lock=True)
            mop.attributes.create_persistent_attribute(
                ctl,
                self.node_name,
                ln="offsetPositive" + axis,
                attributeType="double",
                keyable=True,
            )
            mop.attributes.create_persistent_attribute(
                ctl,
                self.node_name,
                ln="offsetNegative" + axis,
                attributeType="double",
                keyable=True,
            )

        return ctl


exported_rig_modules = [Corrective]
