import logging
import maya.cmds as cmds

from icarus.core.module import RigModule


logger = logging.getLogger(__name__)


class Root(RigModule):

    def initialize(self):
        super(Root, self).initialize()
        self._add_deform_joint()

    def build(self):
        try:
            cmds.makeIdentity(
                self.deform_joints.get()[0],
                apply=True,
                rotate=True
            )
        except RuntimeError:
            logger.warning(
                "couldn't bake the joints' rotation to the jointOrient "
                "because some of the joints are connected to a skinCluster."
            )


exported_rig_modules = [Root]
