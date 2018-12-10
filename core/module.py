import maya.cmds as cmds

class RigModule(object):
    def __init__(self, name, side='M', *args, **kwargs):
        self.name = name
        self.side = side
        self.rig = kwargs.get('rig', None)
        self.node_module = cmds.createNode('transform', name='_'.join([name, side, 'mod']))
