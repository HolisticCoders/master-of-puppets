import maya.cmds as cmds

from icarus.modules.fkikspringchain import FkIkSpringChain
from icarus.core.fields import IntField, ObjectField, ObjectListField
import icarus.metadata


class QuadrupedLeg(FkIkSpringChain):

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
        super(QuadrupedLeg, self).initialize()
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

    def create_driving_joints(self):
        super(QuadrupedLeg, self).create_driving_joints()
        foot_joints = [self.driving_chain[-1]]
        self.foot_driving_joints.set(foot_joints)
        for joint in foot_joints:
            self.driving_chain.remove(joint)

    def build(self):
        super(QuadrupedLeg, self).build()
        self._setup_leg_angle()

        # set the leg in IK by default
        cmds.setAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            1
        )
        cmds.addAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            edit=True,
            defaultValue=1
        )

    def _setup_leg_angle(self):
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='legBendAngle',
            attributeType='double',
            hasMinValue=True,
            minValue=-1,
            hasMaxValue=True,
            maxValue=1,
            keyable=True
        )

        set_range = cmds.createNode('setRange')
        reverse = cmds.createNode('reverse')
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.legBendAngle',
            set_range + '.valueX'
        )
        cmds.setAttr(set_range + '.oldMinX', -1)
        cmds.setAttr(set_range + '.oldMaxX', 1)
        cmds.setAttr(set_range + '.minX', 0)
        cmds.setAttr(set_range + '.maxX', 1)
        cmds.connectAttr(
            set_range + '.outValueX',
            self.ik_handle.get() + '.springAngleBias[0].springAngleBias_FloatValue'
        )
        cmds.connectAttr(
            set_range + '.outValueX',
            reverse + '.inputX'
        )
        cmds.connectAttr(
            reverse + '.outputX',
            self.ik_handle.get() + '.springAngleBias[1].springAngleBias_FloatValue'
        )


exported_rig_modules = [QuadrupedLeg]
