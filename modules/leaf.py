import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField, ObjectField
import icarus.metadata
import icarus.dag
import icarus.attributes


class Leaf(RigModule):

    joint_count = IntField(
        displayable=True,
        editable=True,
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        tooltip="The number of joints for the module.\n"
    )

    def initialize(self):
        super(Leaf, self).initialize()
        for i in xrange(self.joint_count.get()):
            self._add_deform_joint()

    def update(self):
        super(Leaf, self).update()
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
        for joint in self.driving_joints:
            ctl, parent_group = self.add_control(joint, shape_type='sphere')
            cmds.parent(parent_group, self.controls_group.get())
            icarus.dag.matrix_constraint(ctl, joint)

    def update_parent_joint(self):
        """Reparent the joints to the proper parent_joint if needed."""
        super(Leaf, self).update_parent_joint()
        for joint in self.deform_joints.get():
            expected_parent = self.parent_joint.get()
            actual_parent = cmds.listRelatives(joint, parent=True)[0]

            if expected_parent != actual_parent:
                cmds.parent(joint, expected_parent)


exported_rig_modules = [Leaf]

