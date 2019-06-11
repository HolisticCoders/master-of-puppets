import maya.cmds as cmds

from mop.modules.abstract.abstractchain import AbstractChain
from mop.core.fields import (
    IntField,
    ObjectListField,
    ObjectField,
    StringField
)
import mop.metadata


class ChainSwitcher(AbstractChain):

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
        self.chain_a.set(
            cmds.duplicate(
                self.deform_joints,
                renameChildren=True,
                parentOnly=True
            )
        )
        cmds.parent(self.chain_a[0], self.extras_group.get())
        for joint in self.chain_a.get():
            metadata = mop.metadata.metadata_from_name(joint)
            metadata['role'] = 'chainA'
            new_name = mop.metadata.name_from_metadata(metadata)
            cmds.rename(joint, new_name)

        self.chain_b.set(
            cmds.duplicate(
                self.deform_joints,
                renameChildren=True,
                parentOnly=True
            )
        )
        cmds.parent(self.chain_b[0], self.extras_group.get())
        for joint in self.chain_b.get():
            metadata = mop.metadata.metadata_from_name(joint)
            metadata['role'] = 'chainB'
            new_name = mop.metadata.name_from_metadata(metadata)
            cmds.rename(joint, new_name)

    def _create_settings_control(self, node=None):
        """Create the settings control to switch between the two chains.

        :param node: The node on witch the settings control should snap itself.
        :type node: str
        """
        if node is None:
            node = self.deform_joints[-1]
        ctl, buffer_grp = self.add_control(
            node,
            description='settings',
            shape_type='cogwheel'
        )
        self.settings_ctl.set(ctl)
        cmds.parent(buffer_grp, self.controls_group.get())
        mop.dag.matrix_constraint(node, buffer_grp)

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
        settings_ctl = self.settings_ctl.get()
        self.reverse_switch.set(
            self.add_node(
                'reverse',
                description='switch'
            )
        )
        cmds.connectAttr(
            settings_ctl + "." + self.switch_long_name.get(),
            self.reverse_switch.get() + ".inputX"
        )

        for i, deform in enumerate(self.deform_joints):
            a = self.chain_a[i]
            b = self.chain_b[i]
            metadata = mop.metadata.metadata_from_name(a)
            wt_add_mat = self.add_node(
                'wtAddMatrix',
                description = metadata['description'],
                object_id = metadata['id'],
            )
            mult_mat = self.add_node(
                'multMatrix',
                description = metadata['description'],
                object_id = metadata['id'],
            )
            decompose_mat = self.add_node(
                'decomposeMatrix',
                description = metadata['description'],
                object_id = metadata['id'],
            )
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
                deform + '.parentInverseMatrix[0]',
                mult_mat + '.matrixIn[1]',
            )
            cmds.connectAttr(
                mult_mat + ".matrixSum",
                decompose_mat + ".inputMatrix"
            )

            # substract the driven's joint orient from the rotation
            euler_to_quat = self.add_node(
                'eulerToQuat',
                description = metadata['description'],
                object_id = metadata['id'],
            )
            quat_invert = self.add_node(
                'quatInvert',
                description = metadata['description'],
                object_id = metadata['id'],
            )
            quat_prod = self.add_node(
                'quatProd',
                description = metadata['description'],
                object_id = metadata['id'],
            )
            quat_to_euler = self.add_node(
                'quatToEuler',
                description = metadata['description'],
                object_id = metadata['id'],
            )

            cmds.connectAttr(
                deform + '.jointOrient',
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

            # connect the graph to the deform joint's transform attributes
            cmds.connectAttr(
                decompose_mat + '.outputTranslate',
                deform + '.translate'
            )
            cmds.connectAttr(
                quat_to_euler + '.outputRotate',
                deform + '.rotate',
            )
            cmds.connectAttr(
                decompose_mat + '.outputScale',
                deform + '.scale'
            )
