import maya.cmds as cmds

from icarus.modules.chain import Chain
from icarus.core.fields import (
    IntField,
    ObjectListField,
    ObjectField,
    StringField
)
import icarus.metadata


class ChainSwitcher(Chain):

    chain_a = ObjectListField()
    chain_b = ObjectListField()

    # settings control of the arm.
    settings_ctl = ObjectField()
    reverse_switch = ObjectField()

    switch_long_name = StringField()
    switch_nice_name = StringField()
    switch_enum_name = StringField()

    def initialize(self):
        super(ChainSwitcher, self).initialize()
        self.switch_long_name.set('A_B_Switch')
        self.switch_nice_name.set('A/B')
        self.switch_enum_name.set('A:B:')

    def build(self):
        self._create_chains()
        self._create_settings_control()
        self._setup_switch()

    def _create_chains(self):
        chain_a = cmds.duplicate(self.driving_joints, renameChildren=True)
        cmds.parent(chain_a[0], self.extras_group.get())
        for i, joint in enumerate(chain_a):
            metadata = icarus.metadata.metadata_from_name(joint)
            metadata['role'] = 'chainA'
            new_name = icarus.metadata.name_from_metadata(metadata)
            joint = cmds.rename(joint, new_name)
            chain_a[i] = joint

        chain_b = cmds.duplicate(self.driving_joints, renameChildren=True)
        cmds.parent(chain_b[0], self.extras_group.get())
        for i, joint in enumerate(chain_b):
            metadata = icarus.metadata.metadata_from_name(joint)
            metadata['role'] = 'chainB'
            new_name = icarus.metadata.name_from_metadata(metadata)
            joint = cmds.rename(joint, new_name)
            chain_b[i] = joint

        self.chain_a.set(chain_a)
        self.chain_b.set(chain_b)

    def _create_settings_control(self):
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': 'settings',
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        ctl, buffer_grp = self.add_control(
            self.driving_joints[2],
            ctl_name
        )
        self.settings_ctl.set(ctl)
        cmds.parent(buffer_grp, self.controls_group.get())
        icarus.dag.matrix_constraint(self.driving_joints[2], buffer_grp)

        for attr in ['translate', 'rotate', 'scale']:
            for axis in 'XYZ':
                attrName = ctl + '.' + attr + axis
                cmds.setAttr(
                    attrName,
                    lock=True,
                    keyable=False,
                    channelBox=False
                )
        cmds.setAttr(
            ctl + '.visibility',
            lock=True,
            keyable=False,
            channelBox=False
        )

        cmds.addAttr(
            ctl,
            longName=self.switch_long_name.get(),
            niceName=self.switch_nice_name.get(),
            attributeType='enum',
            enumName=self.switch_enum_name.get()
        )
        cmds.setAttr(ctl + "." + self.switch_long_name.get(), keyable=True)

    def _setup_switch(self):
        """Create the necessary nodes to switch between the A and B chains"""
        driving_chain = self.driving_joints
        chain_a = self.chain_a.get()
        chain_b = self.chain_b.get()
        settings_ctl = self.settings_ctl.get()
        self.reverse_switch.set(cmds.createNode('reverse'))
        cmds.connectAttr(
            settings_ctl + "." + self.switch_long_name.get(),
            self.reverse_switch.get() + ".inputX"
        )

        for i in xrange(len(driving_chain)):
            driving = driving_chain[i]
            a = chain_a[i]
            b = chain_b[i]
            wt_add_mat = cmds.createNode('wtAddMatrix')
            mult_mat = cmds.createNode('multMatrix')
            decompose_mat = cmds.createNode('decomposeMatrix')
            cmds.connectAttr(
                a + ".worldMatrix[0]",
                wt_add_mat + ".wtMatrix[0].matrixIn"
            )
            cmds.connectAttr(
                b + ".worldMatrix[0]",
                wt_add_mat + ".wtMatrix[1].matrixIn"
            )
            cmds.connectAttr(
                self.reverse_switch.get() + ".outputX",
                wt_add_mat + ".wtMatrix[0].weightIn"
            )
            cmds.connectAttr(
                settings_ctl + "." + self.switch_long_name.get(),
                wt_add_mat + ".wtMatrix[1].weightIn"
            )
            cmds.connectAttr(
                wt_add_mat + ".matrixSum",
                mult_mat + '.matrixIn[0]',
            )
            cmds.connectAttr(
                driving + '.parentInverseMatrix[0]',
                mult_mat + '.matrixIn[1]',
            )
            cmds.connectAttr(
                mult_mat + ".matrixSum",
                decompose_mat + ".inputMatrix"
            )

            # substract the driven's joint orient from the rotation
            euler_to_quat = cmds.createNode('eulerToQuat')
            quat_invert = cmds.createNode('quatInvert')
            quat_prod = cmds.createNode('quatProd')
            quat_to_euler = cmds.createNode('quatToEuler')

            cmds.connectAttr(
                driving + '.jointOrient',
                euler_to_quat + '.inputRotate',
            )
            cmds.connectAttr(
                euler_to_quat + '.outputQuat',
                quat_invert + '.inputQuat',
            )
            cmds.connectAttr(
                decompose_mat + '.outputQuat',
                quat_prod + '.input1Quat',
            )
            cmds.connectAttr(
                quat_invert + '.outputQuat',
                quat_prod + '.input2Quat',
            )
            cmds.connectAttr(
                quat_prod + '.outputQuat',
                quat_to_euler + '.inputQuat',
            )

            # connect the graph to the driving joint's transform attributes
            cmds.connectAttr(
                decompose_mat + '.outputTranslate',
                driving + '.translate'
            )
            cmds.connectAttr(
                quat_to_euler + '.outputRotate',
                driving + '.rotate',
            )
            cmds.connectAttr(
                decompose_mat + '.outputScale',
                driving + '.scale'
            )
