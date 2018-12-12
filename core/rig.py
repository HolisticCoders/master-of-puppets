import os
import json

import maya.cmds as cmds

from icarus.core.icarusNode import IcarusNode
from icarus.modules import all_rig_modules
from icarus.config import default_modules
from icarus.core.fields import (
    ObjectField,
)


class Rig(IcarusNode):

    modules_group = ObjectField('modules_group')
    extras_group = ObjectField('extras_group')
    rig_modules = ObjectField('rig_modules', as_list=True)
    skeleton = ObjectField('skeleton', as_list=True)

    def __init__(self):
        super(Rig, self).__init__('RIG')
        self._create_basic_hierarchy()
        self._add_default_modules()

    def _create_basic_hierarchy(self):
        if not cmds.objExists('MODULES'):
            self.modules_group.set(cmds.createNode(
                'transform',
                name='MODULES',
            ))
            cmds.parent(self.modules_group.get(), 'RIG')
        if not cmds.objExists('EXTRAS'):
            self.extras_group.set(cmds.createNode(
                'transform',
                name='EXTRAS',
            ))
            cmds.parent(self.extras_group.get(), 'RIG')

    def _add_default_modules(self):
        for module_type, data in default_modules.iteritems():
            self.add_module(module_type, **data)

    def add_module(self, module_type, *args, **kwargs):
        kwargs['rig'] = self
        if module_type not in all_rig_modules:
            raise Exception("Module Type {} is not valid".format(module_type))

        new_module = all_rig_modules[module_type](*args, **kwargs)
        cmds.parent(new_module.name, self.modules_group.get())
        new_module.initialize()
        for joint in new_module.deform_joints.get():
            skel = self.skeleton.get()
            skel.append(joint)
            self.skeleton.set(skel)
        self.rig_modules = self.rig_modules.get().append(new_module)
        return new_module
