import os
import json

import maya.cmds as cmds

from icarus.core.icarusNode import IcarusNode
from icarus.modules import all_rig_modules
from icarus.config import default_modules
from icarus.core.fields import ObjectField


class Rig(IcarusNode):

    modules_group = ObjectField()
    extras_group = ObjectField()
    skeleton_group = ObjectField()

    def __init__(self):
        super(Rig, self).__init__('RIG')
        # stores the instances of the existing rig modules
        self.rig_modules_instances = {}

        if not self.is_initialized.get():
            self._create_basic_hierarchy()

        self._add_default_modules()

    @property
    def rig_modules(self):
        return cmds.listRelatives(self.modules_group)

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
        kwargs['rig'] = self
        if module_type not in all_rig_modules:
            raise Exception("Module Type {} is not valid".format(module_type))

        # instantiate the new module from the list of possible modules.
        new_module = all_rig_modules[module_type](*args, **kwargs)
        cmds.parent(new_module.node_name, self.modules_group.get())
        new_module.initialize()
        new_module.is_initialized.set(True)

        self.rig_modules_instances[new_module.node_name] = new_module

        self.create_skeleton_from_module(new_module)
        return new_module

    def create_skeleton(self):
        # remove the existing rig before re-creating it.
        cmds.delete(cmds.listRelatives(self.skeleton_group.get()))

        for module in self.rig_modules:
            if module not in self.rig_modules_instances:
                # TODO: re-instance the module
                pass
        for module in self.rig_modules_instances.values():
            self.create_skeleton_from_module(module)

    def create_skeleton_from_module(self, module):
        # decide if the joints will be parented to an existing joint
        # or at the root of the skeleton
        parent = module.parent_joint.get()
        if not parent:
            parent = self.skeleton_group.get()

        # duplicate the driving joints and parent them in the rig's skeleton
        # based on the module's parent_joint
        top_driving_joints = cmds.listRelatives(module.driving_group.get())
        all_driving_joints = list(reversed(cmds.listRelatives(
            module.driving_group.get(),
            allDescendents=True
        )))
        deform_joints = []
        for joint in top_driving_joints:
            dupli = cmds.duplicate(
                joint,
                renameChildren=True,
            )
            print "dupli:", dupli
            deform_joints += dupli
            cmds.parent(dupli[0], parent)

        # rename and drive the new deform joints
        for deform, driving, in zip(deform_joints, all_driving_joints):
            deform = cmds.rename(deform, deform.replace('driver1', 'deform'))
            for attr in ['translate', 'rotate', 'scale']:
                for axis in 'XYZ':
                    attr_name = attr + axis
                    deform_attr = '.'.join([deform, attr_name])
                    driving_attr = '.'.join([driving, attr_name])
                    cmds.connectAttr(driving_attr, deform_attr)

