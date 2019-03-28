import maya.cmds as cmds
import maya.api.OpenMaya as om2

from mop.core.module import RigModule
from mop.core.fields import IntField
import mop.dag


class AbstractChain(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1,
        displayable=True,
        editable=True,
        tooltip="The number of joints for the chain."
    )

    def initialize(self):
        super(AbstractChain, self).initialize()
        for i in range(self.joint_count.get()):
            new_joint = self._add_deform_joint()
            if i > 0:
                cmds.setAttr(new_joint + '.translateX', 5)

    def update(self):
        super(AbstractChain, self).update()
        self._update_chain_joint_count()

    def build(self):
        parent = self.controls_group.get()
        for joint in self.driving_joints:
            ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, parent)
            mop.dag.matrix_constraint(ctl, joint)
            parent = ctl

    def _add_deform_joint(self):
        deform_chain = self.deform_joints.get()
        if deform_chain:
            parent = deform_chain[-1]
        else:
            parent = self.parent_joint.get()
        joint = super(AbstractChain, self)._add_deform_joint(
            parent=parent,
            object_id=len(self.deform_joints)
        )
        return joint

    def _update_chain_joint_count(self):
        diff = self.joint_count.get() - len(self.deform_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self._add_deform_joint()
                cmds.setAttr(new_joint + '.translateX', 5)
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
        """Reparent the first joint to the proper parent_joint if needed."""
        super(AbstractChain, self).update_parent_joint()
        expected_parent = self.parent_joint.get()
        first_joint = self.deform_joints[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)
