import maya.cmds as cmds

import mop.metadata

from mop.core.fields import IntField, ObjectListField, ObjectField, EnumField
from mop.modules.fkikrpchain import FkIkRotatePlaneChain
# from mop.common.foot import build_foot


class BipedLeg(FkIkRotatePlaneChain):

    default_side = 'L'

    joint_count = IntField(
        defaultValue=5,
        hasMinValue=True,
        minValue=5,
        hasMaxValue=True,
        maxValue=5,
    )

    foot_driving_joints = ObjectListField()

    twist_placement = ObjectField()
    heel_placement = ObjectField()
    ball_placement = ObjectField()
    tip_placement = ObjectField()
    bank_ext_placement = ObjectField()
    bank_int_placement = ObjectField()

    twist_pivot = ObjectField()
    heel_pivot = ObjectField()
    ball_pivot = ObjectField()
    tip_pivot = ObjectField()
    bank_ext_pivot = ObjectField()
    bank_int_pivot = ObjectField()

    def initialize(self):
        super(BipedLeg, self).initialize()
        self.ik_start_description.set('IK_ankle')
        self.ik_end_description.set('IK_hip')

        name_list = ['hip', 'knee', 'ankle', 'foot_ball', 'foot_tip']

        for deform, name in zip(self.deform_joints.get(), name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name
            }
            deform_name = mop.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)

        self.ball_placement.set(
            self._add_placement_locator(description='foot_ball')
        )

        self.twist_placement.set(
            self._add_placement_locator(description='foot_twist')
        )

        self.tip_placement.set(
            self._add_placement_locator(description='foot_tip')
        )

        self.heel_placement.set(
            self._add_placement_locator(description='foot_heel')
        )

        self.bank_ext_placement.set(
            self._add_placement_locator(description='foot_bank_ext')
        )

        self.bank_int_placement.set(
            self._add_placement_locator(description='foot_bank_int')
        )

    def _create_chains(self):
        super(BipedLeg, self)._create_chains()
        self.ik_chain_end_joint.set(self.chain_b.get()[2])

    def build(self):
        super(BipedLeg, self).build()
        self.build_foot()
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
            endEffector=self.ik_chain_end_joint.get()
        )
        self.ik_handle.set(ik_handle)
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(self.ik_pv_ctl.get(), ik_handle)

    def build_foot(self):
        self.create_foot_pivots()
        self.create_ik_handles()
        self.create_attributes()

        # twist setup
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footTwist',
            self.twist_pivot.get() + '.rotateY'
        )

        # bank setup
        clamp_int = self.add_node(
            'clamp',
            role='clamp',
            description='bank_int'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footBank',
            clamp_int + '.inputR'
        )
        cmds.setAttr(clamp_int + '.maxR', 180)
        cmds.connectAttr(
            clamp_int + '.outputR',
            self.bank_int_pivot.get() + '.rotateZ'
        )

        clamp_ext = self.add_node(
            'clamp',
            role='clamp',
            description='bank_ext'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footBank',
            clamp_ext + '.inputR'
        )
        cmds.setAttr(clamp_ext + '.minR', -180)
        cmds.connectAttr(
            clamp_ext + '.outputR',
            self.bank_ext_pivot.get() + '.rotateZ'
        )

        # heel setup
        clamp = self.add_node(
            'clamp',
            role='clamp',
            description='0_to_neg_90'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footRoll',
            clamp + '.inputR'
        )
        cmds.setAttr(clamp + '.minR', -90)
        cmds.connectAttr(
            clamp + '.outputR',
            self.heel_pivot.get() + '.rotateX'
        )

        # tip setup
        bend_to_straight_percent = self.add_node(
            'setRange',
            role='percent',
            description='bend_to_straight'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.bendLimitAngle',
            bend_to_straight_percent + '.oldMinX'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.toeStraightAngle',
            bend_to_straight_percent + '.oldMaxX'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footRoll',
            bend_to_straight_percent + '.valueX'
        )
        cmds.setAttr(bend_to_straight_percent + '.maxX', 1)

        tip_roll_mult = self.add_node(
            'multDoubleLinear',
            role='mult',
            description='tip_roll'
        )
        cmds.connectAttr(
            bend_to_straight_percent + '.outValueX',
            tip_roll_mult + '.input1'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footRoll',
            tip_roll_mult + '.input2'
        )
        cmds.connectAttr(
            tip_roll_mult + '.output',
            self.tip_pivot.get() + '.rotateX'
        )

        # ball setup
        zero_to_bend_percent = self.add_node(
            'setRange',
            role='percent',
            description='zero_to_bend'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.bendLimitAngle',
            zero_to_bend_percent + '.oldMaxX'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footRoll',
            zero_to_bend_percent + '.valueX'
        )
        cmds.setAttr(zero_to_bend_percent + '.maxX', 1)
        bend_to_straight_reverse = self.add_node(
            'reverse',
            role='reverse',
            description='bend_to_straight'
        )
        cmds.connectAttr(
            bend_to_straight_percent + '.outValueX',
            bend_to_straight_reverse + '.inputX'
        )
        ball_percent_mult = self.add_node(
            'multDoubleLinear',
            role='mult',
            description='ball_percent'
        )
        cmds.connectAttr(
            bend_to_straight_reverse + '.outputX',
            ball_percent_mult + '.input1'
        )
        cmds.connectAttr(
            zero_to_bend_percent + '.outValueX',
            ball_percent_mult + '.input2'
        )
        ball_roll_mult = self.add_node(
            'multDoubleLinear',
            role='mult',
            description='ball_roll'
        )
        cmds.connectAttr(
            ball_percent_mult + '.output',
            ball_roll_mult + '.input1'
        )
        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footRoll',
            ball_roll_mult + '.input2'
        )
        cmds.connectAttr(
            ball_roll_mult + '.output',
            self.ball_pivot.get() + '.rotateX'
        )

    def create_foot_pivots(self):
        pivots_grp = self.add_node(
            'transform',
            role='grp',
            description='foot_roll_pivots'
        )
        mop.dag.snap_first_to_last(pivots_grp, self.extras_group.get())
        cmds.parent(pivots_grp, self.extras_group.get())
        mop.dag.matrix_constraint(self.ik_end_ctl.get(), pivots_grp, maintain_offset=True)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'twist'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.twist_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.twist_pivot.get(),
            self.twist_placement.get()
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'heel'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.heel_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.heel_pivot.get(),
            self.heel_placement.get()
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'ball'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.ball_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.ball_pivot.get(),
            self.ball_placement.get()
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'tip'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.tip_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.tip_pivot.get(),
            self.tip_placement.get()
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'bank_ext'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.bank_ext_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.bank_ext_pivot.get(),
            self.bank_ext_placement.get()
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'bank_int'
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.bank_int_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(
            self.bank_int_pivot.get(),
            self.bank_int_placement.get()
        )

        cmds.parent(self.ball_pivot.get(), self.tip_pivot.get())
        cmds.parent(self.tip_pivot.get(), self.heel_pivot.get())
        cmds.parent(self.heel_pivot.get(), self.bank_int_pivot.get())
        cmds.parent(self.bank_int_pivot.get(), self.bank_ext_pivot.get())
        cmds.parent(self.bank_ext_pivot.get(), self.twist_pivot.get())
        cmds.parent(self.twist_pivot.get(), pivots_grp)

        # Make sure the pivots transform are zeroed out
        # because they'll be driven by attributes that default to a 0 value
        mop.dag.add_parent_group(self.twist_pivot.get())
        mop.dag.add_parent_group(self.heel_pivot.get())
        mop.dag.add_parent_group(self.ball_pivot.get())
        mop.dag.add_parent_group(self.tip_pivot.get())
        mop.dag.add_parent_group(self.bank_ext_pivot.get())
        mop.dag.add_parent_group(self.bank_int_pivot.get())

    def create_ik_handles(self):
        ball_ikHandle, ball_effector = cmds.ikHandle(
            startJoint=self.chain_b[2],  # ankle joint
            endEffector=self.chain_b[3],  # ball joint 
            sol='ikSCsolver'
        )
        cmds.parent(ball_ikHandle, self.ball_pivot.get())

        tip_ikHandle, tip_effector = cmds.ikHandle(
            startJoint=self.chain_b[3],  # ball joint
            endEffector=self.chain_b[4],  # tip joint
            sol='ikSCsolver'
        )
        cmds.parent(tip_ikHandle, self.tip_pivot.get())

        cmds.parent(self.ik_handle.get(), self.ball_pivot.get())

    def create_attributes(self):
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='footRoll',
            attributeType='double',
            hasMinValue=True,
            minValue=-180,
            hasMaxValue=True,
            maxValue=180,
            keyable=True
        )
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='bendLimitAngle',
            attributeType='double',
            defaultValue=45,
            keyable=True
        )
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='toeStraightAngle',
            attributeType='double',
            defaultValue=70,
            keyable=True
        )
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='footTwist',
            attributeType='double',
            keyable=True
        )
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='footBank',
            attributeType='double',
            hasMinValue=True,
            minValue=-180,
            hasMaxValue=True,
            maxValue=180,
            keyable=True
        )


exported_rig_modules = [BipedLeg]
