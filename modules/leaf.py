import maya.cmds as cmds

from mop.core.module import RigModule
from mop.core.fields import IntField, ObjectField
import mop.metadata
import mop.dag
import mop.attributes


class Leaf(RigModule):

    joint_count = IntField(
        displayable=True,
        editable=True,
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        tooltip="The number of joints for the module.\n",
    )

    def create_guide_nodes(self):
        for i in range(self.joint_count.get()):
            self.add_guide_node()

    def create_deform_joints(self):
        for i in range(self.joint_count.get()):
            self.add_deform_joint()

    def constraint_deforms_to_guides(self):
        for guide, deform in zip(self.guide_nodes, self.deform_joints):
            mop.dag.matrix_constraint(guide, deform)

    def update_guide_nodes(self):
        diff = self.joint_count.get() - len(self.guide_nodes)
        if diff > 0:
            for index in range(diff):
                guide = self.add_guide_node()
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
        for joint in self.deform_joints:
            ctl, parent_group = self.add_control(joint, shape_type='sphere')
            cmds.parent(parent_group, self.controls_group.get())
            mop.dag.matrix_constraint(ctl, joint)

    def update_parent_joint(self):
        """Reparent the joints to the proper parent_joint if needed."""
        super(Leaf, self).update_parent_joint()
        for joint in self.deform_joints.get():
            expected_parent = self.parent_joint.get()
            actual_parent = cmds.listRelatives(joint, parent=True)[0]

            if expected_parent != actual_parent:
                cmds.parent(joint, expected_parent)


exported_rig_modules = [Leaf]

