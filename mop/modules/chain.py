import math

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from mop.core.module import RigModule
from mop.core.fields import IntField, ObjectListField
import mop.dag


class Chain(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        displayable=True,
        editable=True,
        tooltip="The number of joints for the chain.",
    )

    def create_guide_nodes(self):
        for i in range(self.joint_count.get()):
            guide = self.add_guide_node()
            if i > 0:
                cmds.setAttr(guide + ".translateX", 5)

    def create_deform_joints(self):
        for i in range(self.joint_count.get()):
            joint = self.add_deform_joint()

    def constraint_deforms_to_guides(self):
        for guide, deform in zip(self.guide_nodes, self.deform_joints):
            mop.dag.matrix_constraint(guide, deform, scale=False)

    def update_guide_nodes(self):
        diff = self.joint_count.get() - len(self.guide_nodes)
        if diff > 0:
            for index in range(diff):
                guide = self.add_guide_node()
                cmds.setAttr(guide + ".translateX", 5)
        elif diff < 0:
            guides = self.guide_nodes.get()
            guides_to_delete = guides[diff:]
            guides_to_keep = guides[: len(guides) + diff]

            cmds.delete(guides_to_delete)

    def update_deform_joints(self):
        diff = self.joint_count.get() - len(self.deform_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self.add_deform_joint()
                cmds.setAttr(new_joint + ".translateX", 5)

        elif diff < 0:
            joints = self.deform_joints.get()
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[: len(joints) + diff]

            for module in self.rig.rig_modules:
                if module.parent_joint in joints_to_delete:
                    if joints_to_keep:
                        new_parent_joint = joints_to_keep[-1]
                    else:
                        new_parent_joint = self.parent_joint.get()
                    module.parent_joint.set(new_parent_joint)
                    module.update()

            cmds.delete(joints_to_delete)

    def build(self):
        parent = self.controls_group.get()
        for joint in self.deform_joints:
            ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, parent)
            mop.dag.matrix_constraint(ctl, joint)
            parent = ctl

    def add_guide_node(
        self,
        parent=None,
        object_id=None,
        skip_id=False,
        description=None,
        shape_type="circle",
    ):
        """Parent the new deform joint to the last one."""
        guide_nodes = self.guide_nodes.get()
        if parent is None:
            if guide_nodes:
                parent = guide_nodes[-1]
            else:
                parent = self.guide_group.get()

        guide = super(Chain, self).add_guide_node(
            parent=parent,
            object_id=object_id,
            skip_id=skip_id,
            description=description,
            shape_type=shape_type,
        )
        return guide

    def add_deform_joint(self, parent=None, object_id=None, description=None):
        """Parent the new deform joint to the last one."""
        deform_joints = self.deform_joints.get()
        if deform_joints:
            parent = deform_joints[-1]
        else:
            parent = self.parent_joint.get()
        joint = super(Chain, self).add_deform_joint(
            parent=parent, object_id=len(self.deform_joints)
        )
        return joint

    def update_parent_joint(self):
        """Reparent the first joint to the proper parent_joint if needed."""
        super(Chain, self).update_parent_joint()
        expected_parent = self.parent_joint.get()
        first_joint = self.deform_joints[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)


exported_rig_modules = [Chain]
