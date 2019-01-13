import maya.cmds as cmds

from icarus.core.module import RigModule
from icarus.core.fields import IntField
import icarus.dag


class Chain(RigModule):

    joint_count = IntField(
        defaultValue=1,
        hasMinValue=True,
        minValue=1
    )

    def initialize(self, *args, **kwargs):
        joints = []
        for i in range(self.joint_count.get()):
            self._add_deform_joint()

    def update(self):
        super(Chain, self).update()
        self._update_joint_count()

    def build(self):
        parent = self.controls_group.get()
        for joint in self.driving_joints:
            ctl, parent_group = self.add_control(joint)
            cmds.parent(parent_group, parent)
            icarus.dag.matrix_constraint(ctl, joint)
            parent = ctl

    def publish(self):
        pass

    def _add_deform_joint(self):
        """Add a new deform joint, child of the last one.
        """
        parent = None
        deform_joints = self.deform_joints.get()
        if deform_joints:
            parent = deform_joints[-1]
        return super(Chain, self)._add_deform_joint(parent=parent)

    def _update_joint_count(self):
        deform_joints = self.deform_joints.get()
        if deform_joints is None:
            deform_joints = []

        diff = self.joint_count.get() - len(deform_joints)
        if diff > 0:
            for index in range(diff):
                new_joint = self._add_deform_joint()
                deform_joints.append(new_joint)
                cmds.setAttr(new_joint + '.translateX', 5)
        elif diff < 0:
            joints = deform_joints
            joints_to_delete = joints[diff:]
            joints_to_keep = joints[:len(joints) + diff]
            deform_joints = joints_to_keep

            for module in self.rig.rig_modules:
                if module.parent_joint.get() in joints_to_delete:
                    if joints_to_keep:
                        new_parent_joint = joints_to_keep[-1]
                    else:
                        new_parent_joint = self.parent_joint.get()
                    module.parent_joint.set(new_parent_joint)
                    module.update()

            cmds.delete(joints_to_delete)
        self.deform_joints.set(deform_joints)

    def update_parent_joint(self):
        """Reparent the first joint to the proper parent_joint if needed."""
        expected_parent = self.parent_joint.get()
        first_joint = self.deform_joints.get()[0]
        actual_parent = cmds.listRelatives(first_joint, parent=True)[0]

        if expected_parent != actual_parent:
            cmds.parent(first_joint, expected_parent)


exported_rig_modules = [Chain]
