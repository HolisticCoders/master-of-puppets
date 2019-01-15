import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.modules.abstract.chainswitcher import ChainSwitcher
from icarus.core.fields import (
    IntField,
    StringField,
    ObjectListField,
    ObjectField,
)
import icarus.metadata


class FkIkChain(ChainSwitcher):

    joint_count = IntField(
        defaultValue=3,
        hasMinValue=True,
        minValue=2
    )

    # list containing the FK controls in the same order as the hierarchy.
    fk_controls = ObjectListField()

    # list containing the IK controls.
    ik_controls = ObjectListField()

    # group containing all the FK controls
    fk_controls_group = ObjectField()

    # group containing all the IK controls
    ik_controls_group = ObjectField()

    ik_handle = ObjectField()
    effector = ObjectField()

    ik_start_description = StringField()
    ik_end_description = StringField()

    def initialize(self):
        super(FkIkChain, self).initialize()

        self.ik_start_description.set('IK_start')
        self.ik_end_description.set('IK_end')
        self.switch_long_name.set('FK_IK_Switch')
        self.switch_nice_name.set('FK/IK')
        self.switch_enum_name.set('FK:IK:')

    def build(self):
        super(FkIkChain, self).build()
        self._setup_fk()
        self._setup_ik()
        self._setup_switch_vis()

    def _create_chains(self):
        """Rename the FK and IK joints."""
        super(FkIkChain, self)._create_chains()

        for fk in self.chain_a:
            metadata = icarus.metadata.metadata_from_name(fk)
            metadata['role'] = 'fk'
            cmds.rename(
                fk,
                icarus.metadata.name_from_metadata(metadata)
            )

        for ik in self.chain_b:
            metadata = icarus.metadata.metadata_from_name(ik)
            metadata['role'] = 'ik'
            cmds.rename(
                ik,
                icarus.metadata.name_from_metadata(metadata)
            )

    def _setup_fk(self):
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'grp',
            'description': 'FK_controls',
        }
        fk_controls_group_name = icarus.metadata.name_from_metadata(metadata)
        self.fk_controls_group.set(
             cmds.createNode('transform', name=fk_controls_group_name)
        )
        cmds.parent(self.fk_controls_group.get(), self.controls_group.get())
        icarus.dag.reset_node(self.fk_controls_group.get())

        parent = self.fk_controls_group.get()
        for i, fk in enumerate(self.chain_a.get()):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'ctl',
                'description': 'FK',
                'id': i
            }
            ctl_name = icarus.metadata.name_from_metadata(metadata)
            ctl, parent_group = self.add_control(fk, ctl_name)
            self.fk_controls.append(ctl)
            cmds.parent(parent_group, parent)
            icarus.dag.matrix_constraint(ctl, fk)
            parent = ctl

    def _setup_ik(self):
        ik_chain = self.chain_b.get()
        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'grp',
            'description': 'IK_controls',
        }
        ik_controls_group_name = icarus.metadata.name_from_metadata(metadata)
        self.ik_controls_group.set(
             cmds.createNode('transform', name=ik_controls_group_name)
        )
        cmds.parent(self.ik_controls_group.get(), self.controls_group.get())
        icarus.dag.reset_node(self.ik_controls_group.get())

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': self.ik_end_description.get(),
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        end_ctl, parent_group = self.add_control(
            ik_chain[-1],
            ctl_name,
            'cube'
        )
        self.ik_controls.append(end_ctl)
        cmds.setAttr(parent_group + '.rotate', 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        icarus.dag.matrix_constraint(
            end_ctl,
            ik_chain[-1],
            translate=False,
            rotate=True,
            scale=False,
            maintain_offset=True
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': self.ik_start_description.get(),
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        start_ctl, parent_group = self.add_control(
            ik_chain[0],
            ctl_name,
            'cube'
        )
        self.ik_controls.append(start_ctl)
        cmds.setAttr(parent_group + '.rotate', 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        icarus.dag.matrix_constraint(
            start_ctl,
            ik_chain[0],
            maintain_offset=True
        )

        metadata = {
            'base_name': self.name.get(),
            'side': self.side.get(),
            'role': 'ctl',
            'description': 'IK_pole_vector',
        }
        ctl_name = icarus.metadata.name_from_metadata(metadata)
        pole_vector_ctl, parent_group = self.add_control(
            ik_chain[-1],
            ctl_name,
            'sphere'
        )
        self.ik_controls.append(pole_vector_ctl)
        self._place_pole_vector(parent_group)
        cmds.xform(parent_group, rotation=[0, 0, 0], worldSpace=True)
        cmds.parent(parent_group, self.ik_controls_group.get())

        ik_handle, effector = cmds.ikHandle(
            startJoint=ik_chain[0],
            endEffector=ik_chain[2]
        )
        cmds.parent(ik_handle, self.extras_group.get())
        cmds.poleVectorConstraint(pole_vector_ctl, ik_handle)
        icarus.dag.matrix_constraint(
            end_ctl,
            ik_handle,
            maintain_offset=True
        )

    def _place_pole_vector(self, ctl):
        ik_chain = self.chain_b.get()
        start_pos = cmds.xform(
            ik_chain[0],
            query=True,
            worldSpace=True,
            translation=True
        )
        elbow_pos = cmds.xform(
            ik_chain[1],
            query=True,
            worldSpace=True,
            translation=True
        )
        end_pos = cmds.xform(
            ik_chain[2],
            query=True,
            worldSpace=True,
            translation=True
        )

        start_vec = om2.MVector(*start_pos)
        elbow_vec = om2.MVector(*elbow_pos)
        end_vec = om2.MVector(*end_pos)

        start_end_vec = end_vec - start_vec
        shouler_elbow_vec = elbow_vec - start_vec

        dot_product = shouler_elbow_vec * start_end_vec
        proj = float(dot_product) / float(start_end_vec.length())
        start_end_vec_norm = start_end_vec.normal()
        projection_vec = start_end_vec_norm * proj

        pole_vec = shouler_elbow_vec - projection_vec
        pole_vec *= 10
        pv_control_vec = pole_vec + elbow_vec
        cmds.xform(ctl, worldSpace=1, translation=pv_control_vec)

    def _setup_switch_vis(self):
        settings_ctl = self.settings_ctl.get()
        cmds.connectAttr(
            self.reverse_switch.get() + '.outputX',
            self.fk_controls_group.get() + '.visibility'
        )
        cmds.connectAttr(
            settings_ctl + '.' + self.switch_long_name.get(),
            self.ik_controls_group.get() + '.visibility'
        )


exported_rig_modules = [FkIkChain]
