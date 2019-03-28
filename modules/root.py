import logging
import maya.cmds as cmds

from mop.core.module import RigModule


logger = logging.getLogger(__name__)


class Root(RigModule):

    def initialize(self):
        super(Root, self).initialize()
        self._add_deform_joint()

    def build(self):
        pass


exported_rig_modules = [Root]
