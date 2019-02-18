import maya.cmds as cmds

from icarus.modules.fkikrpchain import FkIkRotatePlaneChain
from icarus.core.fields import IntField, ObjectListField, ObjectField, EnumField
import icarus.dag
import icarus.metadata


class Arm(FkIkRotatePlaneChain):

    def initialize(self):
        super(Arm, self).initialize()
        self.side.set('L')
        self.ik_start_description.set('IK_shoulder')
        self.ik_end_description.set('IK_wrist')

        name_list = ['shoulder', 'elbow', 'wrist']

        for deform, name in zip(self.deform_chain.get(), name_list):
            metadata = {
                'base_name': self.name.get(),
                'side': self.side.get(),
                'role': 'deform',
                'description': name
            }
            deform_name = icarus.metadata.name_from_metadata(metadata)
            deform = cmds.rename(deform, deform_name)

    def build(self):
        super(Arm, self).build()
        cmds.setAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            1
        )
        cmds.addAttr(
            self.settings_ctl.get() + '.' + self.switch_long_name.get(),
            edit=True,
            defaultValue=1
        )


exported_rig_modules = [Arm]
