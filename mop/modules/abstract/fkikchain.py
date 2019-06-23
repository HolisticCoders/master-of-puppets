import maya.api.OpenMaya as om2
import maya.cmds as cmds

from mop.core.fields import IntField, StringField, ObjectListField, ObjectField
from mop.modules.abstract.chainswitcher import ChainSwitcher
import mop.metadata


class FkIkChain(ChainSwitcher):

    # list containing the FK controls in the same order as the hierarchy.
    fk_controls = ObjectListField()

    # list containing the IK controls.
    ik_controls = ObjectListField()
    ik_start_ctl = ObjectField()
    ik_end_ctl = ObjectField()
    ik_pv_ctl = ObjectField()

    # group containing all the FK controls
    fk_controls_group = ObjectField()

    # group containing all the IK controls
    ik_controls_group = ObjectField()

    ik_handle = ObjectField()
    effector = ObjectField()

    ik_start_description = StringField()
    ik_end_description = StringField()
    ik_chain_end_joint = ObjectField()

    def initialize(self):
        super(FkIkChain, self).initialize()

        self.ik_start_description.set("IK_start")
        self.ik_end_description.set("IK_end")
        self.switch_long_name.set("FK_IK_Switch")
        self.switch_nice_name.set("FK/IK")
        self.switch_enum_name.set("FK:IK:")

    def _create_chains(self):
        """Rename the FK and IK joints."""
        super(FkIkChain, self)._create_chains()

        for fk in self.chain_a:
            metadata = mop.metadata.metadata_from_name(fk)
            metadata["role"] = "fk"
            cmds.rename(fk, mop.metadata.name_from_metadata(metadata))

        for ik in self.chain_b:
            cmds.setAttr(ik + ".jointOrient", lock=False)
            metadata = mop.metadata.metadata_from_name(ik)
            metadata["role"] = "ik"
            cmds.rename(ik, mop.metadata.name_from_metadata(metadata))
        cmds.makeIdentity(self.chain_b[0], apply=True, rotate=True)

    def build(self):
        super(FkIkChain, self).build()
        self._setup_fk()
        self._setup_ik()
        self._setup_switch_vis()

    def _setup_fk(self):
        self.fk_controls_group.set(
            self.add_node("transform", role="grp", description="FK_controls")
        )
        cmds.parent(self.fk_controls_group.get(), self.controls_group.get())
        mop.dag.reset_node(self.fk_controls_group.get())

        parent = self.fk_controls_group.get()
        for i, fk in enumerate(self.chain_a.get()):
            metadata = mop.metadata.metadata_from_name(fk)
            if metadata["description"]:
                description = "FK_" + metadata["description"]
            else:
                description = None
            ctl, parent_group = self.add_control(fk, description=description)
            self.fk_controls.append(ctl)
            cmds.parent(parent_group, parent)
            mop.dag.matrix_constraint(ctl, fk)
            parent = ctl

    def _setup_ik(self):
        ik_chain = self.chain_b.get()
        if not self.ik_chain_end_joint.get():
            self.ik_chain_end_joint.set(ik_chain[-1])
        self.ik_controls_group.set(
            self.add_node("transform", role="grp", description="IK_controls")
        )
        cmds.parent(self.ik_controls_group.get(), self.controls_group.get())
        mop.dag.reset_node(self.ik_controls_group.get())
        # print(self.ik_chain_end_joint.get())
        end_ctl, parent_group = self.add_control(
            self.ik_chain_end_joint.get(),
            description=self.ik_end_description.get(),
            shape_type="cube",
        )
        self.ik_controls.append(end_ctl)
        self.ik_end_ctl.set(end_ctl)
        cmds.setAttr(parent_group + ".rotate", 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        mop.dag.matrix_constraint(
            end_ctl,
            self.ik_chain_end_joint.get(),
            translate=False,
            rotate=True,
            scale=False,
            maintain_offset=True,
        )

        start_ctl, parent_group = self.add_control(
            ik_chain[0], description=self.ik_start_description.get(), shape_type="cube"
        )
        self.ik_controls.append(start_ctl)
        self.ik_start_ctl.set(start_ctl)
        cmds.setAttr(parent_group + ".rotate", 0, 0, 0)
        cmds.parent(parent_group, self.ik_controls_group.get())
        mop.dag.matrix_constraint(start_ctl, ik_chain[0], maintain_offset=True)

        pole_vector_ctl, parent_group = self.add_control(
            self.ik_chain_end_joint.get(),
            description="IK_pole_vector",
            shape_type="sphere",
        )
        self.ik_controls.append(pole_vector_ctl)
        self.ik_pv_ctl.set(pole_vector_ctl)
        self._place_pole_vector()
        cmds.xform(parent_group, rotation=[0, 0, 0], worldSpace=True)
        cmds.parent(parent_group, self.ik_controls_group.get())

        self._create_ik_handle()

    def _create_ik_handle(self):
        raise NotImplementedError()

    def _place_pole_vector(self):
        raise NotImplementedError()

    def _setup_switch_vis(self):
        settings_ctl = self.settings_ctl.get()
        cmds.connectAttr(
            self.reverse_switch.get() + ".outputX",
            self.fk_controls_group.get() + ".visibility",
        )
        cmds.connectAttr(
            settings_ctl + "." + self.switch_long_name.get(),
            self.ik_controls_group.get() + ".visibility",
        )
