import maya.cmds as cmds


class CatchCreatedNodes(object):
    def __init__(self):
        self.nodes = []
        self.before_nodes = set()
        self.after_nodes = set()

    def __enter__(self):
        self.before_nodes = set(cmds.ls('*'))
        return self.nodes

    def __exit__(self, *args):
        self.after_nodes = set(cmds.ls('*'))
        self.nodes.extend(list(self.after_nodes - self.before_nodes))
