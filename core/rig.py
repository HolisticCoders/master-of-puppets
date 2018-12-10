import maya.cmds as cmds

from icarus.core.icarusNode import IcarusNode
from icarus.modules import all_rig_modules

class Rig(object):
    def __init__(self):
        self.create_basic_hierarchy()
        self.modules = []

    def create_basic_hierarchy(self):
        if not cmds.objExists('RIG'):
            self.rig_group = cmds.createNode('transform', name='RIG')
        if not cmds.objExists('MODULES'):
            self.modules_group = cmds.createNode('transform', name='MODULES', parent='RIG')
        if not cmds.objExists('EXTRAS'):
            self.extras_group = cmds.createNode('transform', name='EXTRAS', parent='RIG')

    def add_module(self, module_type, *args, **kwargs):
        kwargs['rig'] = self
        if module_type not in all_rig_modules:
            raise Exception("Module Type {} is not valid".format(module_type))

        new_module = all_rig_modules[module_type](*args, **kwargs)
        cmds.parent(new_module.node_module, self.modules_group)
        self.modules.append(new_module)
        return new_module
