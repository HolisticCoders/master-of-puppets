import maya.cmds as cmds

import icarus.metadata

from icarus.core.fields import IntField, ObjectListField, ObjectField
from icarus.modules.fkikrpchain import FkIkRPChain
from icarus.common.foot import build_foot


class BipedLeg(FkIkRPChain):

    joint_count = IntField(
        defaultValue=5,
        hasMinValue=True,
        minValue=5,
        hasMaxValue=True,
        maxValue=5,
    )

    foot_driving_joints = ObjectListField()

    heel_placement = ObjectField()
    ball_placement = ObjectField()
    tip_placement = ObjectField()

    heel_pivot = ObjectField()
    ball_pivot = ObjectField()
    tip_pivot = ObjectField()

    def initialize(self):
        super(BipedLeg, self).initialize()
        self.ik_start_description.set('IK_ankle')
        self.ik_end_description.set('IK_hip')

        name_list = ['hip', 'knee', 'ankle', 'foot_ball', 'foot_tip']

        for deform, name in zip(self.deform_chain.get(), name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name
            }
            deform_name = icarus.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'placement',
            'description': 'foot_ball'
        }
        name = icarus.metadata.name_from_metadata(metadata)
        self._add_placement_locator(name=name)
        self.ball_placement.set(name)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'placement',
            'description': 'foot_tip'
        }
        name = icarus.metadata.name_from_metadata(metadata)
        self._add_placement_locator(name=name)
        self.tip_placement.set(name)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'placement',
            'description': 'foot_heel'
        }
        name = icarus.metadata.name_from_metadata(metadata)
        self._add_placement_locator(name=name)
        self.heel_placement.set(name)

    def create_driving_joints(self):
        super(BipedLeg, self).create_driving_joints()
        foot_joints = [j for j in self.driving_chain if 'foot' in j]
        self.foot_driving_joints.set(foot_joints)
        for joint in foot_joints:
            self.driving_chain.remove(joint)

    def build(self):
        super(BipedLeg, self).build()
        build_foot(self)
        cmds.setAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            1
        )
        cmds.addAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            edit=True,
            defaultValue=1
        )

    def _create_ik_handle(self):
        """Overriden to NOT constrain the ik handle.
        """
        ik_chain = self.chain_b.get()
        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],
            endEffector=ik_chain[2]
        )
        self.ik_handle.set(ik_handle)
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(self.ik_pv_ctl.get(), ik_handle)


exported_rig_modules = [BipedLeg]
