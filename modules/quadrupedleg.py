import maya.cmds as cmds

from icarus.modules.fkikspringchain import FkIkSpringChain
from icarus.core.fields import IntField


class QuadrupedLeg(FkIkSpringChain):

    joint_count = IntField(
        defaultValue=4,
        hasMinValue=True,
        minValue=4,
        hasMaxValue=True,
        maxValue=4,
    )

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
