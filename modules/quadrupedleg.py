import maya.cmds as cmds
import maya.mel as mel

from mop.modules.fkikspringchain import FkIkSpringChain
from mop.core.fields import IntField, ObjectField, ObjectListField, EnumField
import mop.metadata


class QuadrupedLeg(FkIkSpringChain):

    default_side = 'L'

    joint_count = IntField(
        defaultValue=5, hasMinValue=True, minValue=5, hasMaxValue=True, maxValue=5
    )

    twist_guide = ObjectField()
    heel_guide = ObjectField()
    tip_guide = ObjectField()
    bank_ext_guide = ObjectField()
    bank_int_guide = ObjectField()

    twist_pivot = ObjectField()
    heel_pivot = ObjectField()
    tip_pivot = ObjectField()
    bank_ext_pivot = ObjectField()
    bank_int_pivot = ObjectField()

    def __init__(self, *args, **kwargs):
        self.name_list = ['hip', 'knee', 'ankle', 'foot_ball', 'foot_tip']
        super(QuadrupedLeg, self).__init__(*args, **kwargs)

    def initialize(self):
        super(QuadrupedLeg, self).initialize()
        self.ik_start_description.set('IK_ankle')
        self.ik_end_description.set('IK_hip')

    def create_guide_nodes(self):
        super(QuadrupedLeg, self).create_guide_nodes()

        for guide, name in zip(self.guide_nodes.get(), self.name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'guide',
                'description': name,
            }
            name = mop.metadata.name_from_metadata(metadata)
            cmds.rename(guide, name)

        parent = self.guide_group.get()

        self.twist_guide.set(
            self.add_guide_node(
                parent=parent,
                description='foot_twist_pivot',
                shape_type='sphere',
                skip_id=True,
            )
        )

        self.heel_guide.set(
            self.add_guide_node(
                parent=parent,
                description='foot_heel_pivot',
                shape_type='sphere',
                skip_id=True,
            )
        )

        self.tip_guide.set(
            self.add_guide_node(
                parent=parent,
                description='foot_tip_pivot',
                shape_type='sphere',
                skip_id=True,
            )
        )

        self.bank_ext_guide.set(
            self.add_guide_node(
                parent=parent,
                description='foot_bank_ext_pivot',
                shape_type='sphere',
                skip_id=True,
            )
        )

        self.bank_int_guide.set(
            self.add_guide_node(
                parent=parent,
                description='foot_bank_int_pivot',
                shape_type='sphere',
                skip_id=True,
            )
        )

    def create_deform_joints(self):
        super(QuadrupedLeg, self).create_deform_joints()

        for deform, name in zip(self.deform_joints.get(), self.name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name,
            }
            name = mop.metadata.name_from_metadata(metadata)
            cmds.rename(deform, name)

    def _create_chains(self):
        super(QuadrupedLeg, self)._create_chains()
        self.ik_chain_end_joint.set(self.chain_b.get()[3])

    def _create_settings_control(self):
        super(QuadrupedLeg, self)._create_settings_control(self.deform_joints[3])

    def _create_ik_handle(self):
        ik_chain = self.chain_b.get()
        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],  # hip
            endEffector=self.ik_chain_end_joint.get(),  # ankle
            solver='ikSpringSolver',
        )
        self.ik_handle.set(ik_handle)
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(self.ik_pv_ctl.get(), ik_handle)

    def build(self):
        super(QuadrupedLeg, self).build()
        self._setup_leg_angle()
        self._setup_foot()

        # set the leg in IK by default
        cmds.setAttr(self.settings_ctl.get() + '.' + self.switch_long_name.get(), 1)
        cmds.addAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            edit=True,
            defaultValue=1,
        )

    def _setup_leg_angle(self):
        cmds.addAttr(
            self.ik_end_ctl.get(),
            longName='legBendAngle',
            attributeType='double',
            hasMinValue=True,
            minValue=-10,
            hasMaxValue=True,
            maxValue=10,
            keyable=True,
        )

        set_range = self.add_node('setRange', description='legBendAngle')
        reverse = self.add_node('reverse', description='legBendAngle')
        cmds.connectAttr(self.ik_end_ctl.get() + '.legBendAngle', set_range + '.valueX')
        cmds.setAttr(set_range + '.oldMinX', -10)
        cmds.setAttr(set_range + '.oldMaxX', 10)
        cmds.setAttr(set_range + '.minX', 0)
        cmds.setAttr(set_range + '.maxX', 1)

        cmds.select(self.ik_handle.get())

        command = 'cmds.connectAttr("{}.outValueX", "{}.springAngleBias[0].springAngleBias_FloatValue")'.format(
            set_range, self.ik_handle.get()
        )
        cmds.evalDeferred(command)

        cmds.connectAttr(set_range + '.outValueX', reverse + '.inputX')

        command = 'cmds.connectAttr("{}.outputX", "{}.springAngleBias[1].springAngleBias_FloatValue")'.format(
            reverse, self.ik_handle.get()
        )
        cmds.evalDeferred(command)

    def _setup_foot(self):
        self._add_foot_attributes()
        self._create_foot_pivots()
        self._connect_attrs_to_pivots()
        mop.dag.matrix_constraint(
            self.bank_int_pivot.get(), self.ik_handle.get(), maintain_offset=True
        )
        tip_ik_handle, effector = cmds.ikHandle(
            startJoint=self.chain_b[-2],  # ball joint
            endEffector=self.chain_b[-1],  # tip joint
            sol='ikSCsolver',
        )
        cmds.parent(tip_ik_handle, self.bank_int_pivot.get())

    def _add_foot_attributes(self):
        ctl = self.ik_end_ctl.get()
        cmds.addAttr(
            ctl,
            longName='footRoll',
            attributeType='double',
            hasMinValue=True,
            minValue=-180,
            hasMaxValue=True,
            maxValue=180,
            keyable=True,
        )
        cmds.addAttr(ctl, longName='footTwist', attributeType='double', keyable=True)
        cmds.addAttr(
            ctl,
            longName='footBank',
            attributeType='double',
            hasMinValue=True,
            minValue=-180,
            hasMaxValue=True,
            maxValue=180,
            keyable=True,
        )

    def _create_foot_pivots(self):
        pivots_grp = self.add_node('transform', role='grp', description='foot_pivots')
        mop.dag.snap_first_to_last(pivots_grp, self.extras_group.get())
        cmds.parent(pivots_grp, self.extras_group.get())
        mop.dag.matrix_constraint(
            self.ik_end_ctl.get(), pivots_grp, maintain_offset=True
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'twist',
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.twist_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(self.twist_pivot.get(), self.twist_guide.get())
        cmds.parent(self.twist_pivot.get(), pivots_grp)

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'heel',
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.heel_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(self.heel_pivot.get(), self.heel_guide.get())
        cmds.parent(self.heel_pivot.get(), self.twist_pivot.get())

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'tip',
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.tip_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(self.tip_pivot.get(), self.tip_guide.get())
        cmds.parent(self.tip_pivot.get(), self.heel_pivot.get())

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'bank_ext',
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.bank_ext_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(self.bank_ext_pivot.get(), self.bank_ext_guide.get())
        cmds.parent(self.bank_ext_pivot.get(), self.tip_pivot.get())

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'pivot',
            'description': 'bank_int',
        }
        name = mop.metadata.name_from_metadata(metadata)
        self.bank_int_pivot.set(cmds.spaceLocator(name=name)[0])
        mop.dag.snap_first_to_last(self.bank_int_pivot.get(), self.bank_int_guide.get())
        cmds.parent(self.bank_int_pivot.get(), self.bank_ext_pivot.get())

    def _connect_attrs_to_pivots(self):
        clamp_tip = self.add_node('clamp', description='tip')
        clamp_heel = self.add_node('clamp', description='heel')
        cmds.connectAttr(self.ik_end_ctl.get() + '.footRoll', clamp_tip + '.inputR')
        cmds.connectAttr(self.ik_end_ctl.get() + '.footRoll', clamp_heel + '.inputR')
        cmds.setAttr(clamp_heel + '.minR', -180)
        cmds.setAttr(clamp_tip + '.maxR', 180)
        cmds.connectAttr(clamp_heel + '.outputR', self.heel_pivot.get() + '.rotateX')
        cmds.connectAttr(clamp_tip + '.outputR', self.tip_pivot.get() + '.rotateX')

        cmds.connectAttr(
            self.ik_end_ctl.get() + '.footTwist', self.twist_pivot.get() + '.rotateY'
        )
        clamp_int = self.add_node('clamp', description='int')
        clamp_ext = self.add_node('clamp', description='ext')
        cmds.connectAttr(self.ik_end_ctl.get() + '.footBank', clamp_int + '.inputR')
        cmds.connectAttr(self.ik_end_ctl.get() + '.footBank', clamp_ext + '.inputR')
        cmds.setAttr(clamp_int + '.minR', -180)
        cmds.setAttr(clamp_ext + '.maxR', 180)
        cmds.connectAttr(clamp_int + '.outputR', self.bank_ext_pivot.get() + '.rotateZ')
        cmds.connectAttr(clamp_ext + '.outputR', self.bank_int_pivot.get() + '.rotateZ')


exported_rig_modules = [QuadrupedLeg]
