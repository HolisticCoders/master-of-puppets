import maya.cmds as cmds


class IcarusNode(object):
    def __init__(self, name, node_type=None, parent=None):
        """Create the node if it doesn't already exist."""
        self.name = name
        if not cmds.objExists(name):
            if node_type is None:
                node_type = 'transform'
            elif node_type not in cmds.allNodeTypes():
                raise Exception("Specified `{}` node_type is not a valid maya node.".format(node_type))
                return
            if parent is not None and not cmds.objExists(parent):
                raise Exception("Parent node `{}` does not exist.".format(parent))
                return
            cmds.createNode(node_type, name=name, parent=parent)

