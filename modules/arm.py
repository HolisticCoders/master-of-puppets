import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.modules.fkikrpchain import FkIkRPChain
from icarus.core.fields import IntField, ObjectListField, ObjectField
import icarus.dag
import icarus.metadata


class Arm(FkIkRPChain):

    def initialize(self):
        super(Arm, self).initialize()
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


exported_rig_modules = [Arm]
