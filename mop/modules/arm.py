import maya.cmds as cmds

from mop.modules.fkikrpchain import FkIkRotatePlaneChain
from mop.core.fields import IntField, ObjectListField, ObjectField, EnumField
import mop.dag
import mop.metadata


class Arm(FkIkRotatePlaneChain):

    default_side = "L"

    def initialize(self):
        super(Arm, self).initialize()
        self.ik_start_description.set("IK_shoulder")
        self.ik_end_description.set("IK_wrist")

        name_list = ["shoulder", "elbow", "wrist"]

        for deform, name in zip(self.deform_joints, name_list):
            metadata = {
                "base_name": self.name.get(),
                "side": self.side.get(),
                "role": "deform",
                "description": name,
            }
            deform_name = mop.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)

    def build(self):
        super(Arm, self).build()
        cmds.setAttr(self.settings_ctl.get() + "." + self.switch_long_name.get(), 1)
        cmds.addAttr(
            self.settings_ctl.get() + "." + self.switch_long_name.get(),
            edit=True,
            defaultValue=1,
        )

    def update_guide_nodes(self):
        """Don't update as the leg has a fixed number of guides"""
        return

    def update_deform_joints(self):
        """Don't update as the leg has a fixed number of joints"""
        return


exported_rig_modules = [Arm]
