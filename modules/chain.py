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
        self._update_joint_count()

    def build(self):
        parent = self.controls_group.get()
        for joint in self.driving_joints:
            ctl = cmds.circle(name=joint + '_ctl')[0]

            icarus.dag.snap_first_to_last(ctl, joint)
            cmds.parent(ctl, parent)

            parent_group = icarus.dag.add_parent_group(ctl, 'buffer')
            icarus.dag.matrix_constraint(ctl, joint)

            parent = ctl

    def publish(self):
        pass

    def _add_deform_joint(self):
        """Add a new deform joint, child of the last one.
        """
        parent = None
        deform_joints = self.deform_joints_list.get()
        if deform_joints:
            parent = deform_joints[-1]
        return super(Chain, self)._add_deform_joint(parent=parent)

    def _update_joint_count(self):
        deform_joints = self.deform_joints_list.get()
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
            cmds.delete(joints_to_delete)
        self.deform_joints_list.set(deform_joints)


exported_rig_modules = [Chain]