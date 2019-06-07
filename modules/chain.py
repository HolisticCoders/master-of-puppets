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
        tooltip="The number of joints for the chain."
    )


    def create_guide_nodes(self):
        diff = self.joint_count.get() - len(self.guide_nodes)
        if diff > 0:
            for index in range(diff):
                guide = self.add_guide_node()
                cmds.setAttr(guide + '.translateX', 5)
        elif diff < 0:
            guides = self.guide_nodes.get()
            guides_to_delete = guides[diff:]
            guides_to_keep = guides[:len(guides) + diff]

            cmds.delete(guides_to_delete)


    def create_deform_joints(self):
        diff = self.joint_count.get() - len(self.deform_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self.add_deform_joint()
                cmds.setAttr(new_joint + '.translateX', 5)
                self.end_joint.set(new_joint)

                # parent the child modules to the new last_joint
                for module in self.rig.rig_modules:
                    if module.parent_module == self:
                        module.update()

        elif diff < 0:
            joints = self.deform_joints.get()
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]
            self.end_joint.set(joints_to_keep[-1])

            # parent the child modules to the new last_joint
            for module in self.rig.rig_modules:
                if module.parent_module == self:
                    module.update()

            cmds.delete(joints_to_delete)


    def build(self):
        parent = self.controls_group.get()
        for joint in self.deform_joints:
            ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, parent)
            mop.dag.matrix_constraint(ctl, joint)
            parent = ctl

    def add_guide_node(self):
        """Parent the new deform joint to the last one."""
        guide_nodes = self.guide_nodes.get()
        if guide_nodes:
            parent = guide_nodes[-1]
        else:
            parent = self.guide_group.get()
        guide = super(Chain, self).add_guide_node(
            parent=parent,
            object_id=len(self.guide_nodes)
        )
        return guide


    def add_deform_joint(self):
        """Parent the new deform joint to the last one."""
        deform_joints = self.deform_joints.get()
        if deform_joints:
            parent = deform_joints[-1]
        else:
            parent = self.parent_module.end_joint.get()
        joint = super(Chain, self).add_deform_joint(
            parent=parent,
            object_id=len(self.deform_joints)
        )
        return joint

    def constraint_deforms_to_guides(self):
        for guide, deform in zip(self.guide_nodes, self.deform_joints):
            mop.dag.matrix_constraint(guide, deform)

    def update_parent_joint(self):
        """Reparent the first joint to the proper parent_joint if needed."""
        super(Chain, self).update_parent_joint()
        expected_parent = self.parent_module.end_joint.get()
        first_joint = self.deform_joints[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)


exported_rig_modules = [Chain]
