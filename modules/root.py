import maya.cmds as cmds

from icarus.core.module import RigModule
import icarus.metadata

class Root(RigModule):

    def initialize(self):
        joint_name = icarus.metadata.name_from_metadata(
            self.name,
            self.side,
            'driver',
        )
        self._add_driving_joint(name=joint_name)

    def update(self):
        pass

    def build(self):
        pass

    def publish(self):
        pass

exported_rig_modules = [Root]
