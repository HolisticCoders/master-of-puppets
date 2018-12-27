import os
import json

import maya.cmds as cmds

from icarus.core.icarusNode import IcarusNode
from icarus.modules import all_rig_modules
from icarus.config import default_modules
from icarus.core.fields import ObjectField
import icarus.dag


class Rig(IcarusNode):

    modules_group = ObjectField()
    extras_group = ObjectField()
    skeleton_group = ObjectField()

    def __init__(self):
        super(Rig, self).__init__('RIG')

        if not self.is_initialized.get():
            self._create_basic_hierarchy()
            self._add_default_modules()
            self.is_initialized.set(True)

    @property
    def rig_modules(self):
        modules = []
        for node in cmds.listRelatives(self.modules_group.get()) or []:
            module_type = cmds.getAttr(node + '.module_type')
            module = all_rig_modules[module_type](node, rig=self)
            modules.append(module)

        return modules

    @property
    def skeleton(self):
        return cmds.listRelatives(self.skeleton_group.get(), allDescendents=True)

    @property
    def build_nodes(self):
        all_nodes = cmds.ls('*')
        build_nodes = []
        for node in all_nodes:
            if cmds.attributeQuery('is_build_node', node=node, exists=True):
                build_nodes.append(node)
        return build_nodes

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
        if not cmds.objExists('SKELETON'):
            self.skeleton_group.set(cmds.createNode(
                'transform',
                name='SKELETON',
            ))
            cmds.parent(self.skeleton_group.get(), 'RIG')

    def _add_default_modules(self):
        for module_type, data in default_modules.iteritems():
            self.add_module(module_type, **data)

    def add_module(self, module_type, *args, **kwargs):
        if module_type not in all_rig_modules:
            raise Exception("Module Type {} is not valid".format(module_type))

        # instantiate the new module from the list of possible modules.
        kwargs['rig'] = self
        new_module = all_rig_modules[module_type](*args, **kwargs)
        parent = cmds.listRelatives(new_module.node_name, parent=True)
        if not parent or parent[0] != self.modules_group.get():
            cmds.parent(new_module.node_name, self.modules_group.get())

        # self.create_skeleton_from_module(new_module)
        return new_module

    def build(self):
        nodes_before_build = set(cmds.ls('*'))
        for module in self.rig_modules:
            module._build()
        nodes_after_build = set(cmds.ls('*'))
        build_nodes = list(nodes_after_build - nodes_before_build)
        self._tag_nodes_for_unbuild(build_nodes)

    def unbuild(self):
        self.reset_pose()
        for node in self.skeleton:
            for attribute in ['.translate', '.rotate', '.scale']:
                attr = node + attribute
                input_attr = cmds.connectionInfo(attr, sourceFromDestination=True)
                cmds.disconnectAttr(input_attr, attr)
        cmds.delete(self.build_nodes)
        for module in self.rig_modules:
            module.is_built.set(False)

    def reset_pose(self):
        for control in cmds.ls('*_ctl'):
            icarus.dag.reset_node(control)

    def _tag_nodes_for_unbuild(self, nodes):
        """Tag the nodes created during the build.

        this will allow to delete them easily later on.
        """
        for node in nodes:
            cmds.addAttr(
                node,
                longName='is_build_node',
                attributeType='bool',
                defaultValue=True
            )




