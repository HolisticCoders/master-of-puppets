import maya.cmds as cmds


class IcarusNode(object):
    def __init__(self, name, node_type=None, parent=None):
        """Create the node if it doesn't already exist."""
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
        self.name = name

    def __getattr__(self, attr):
        """Get the attribute from the maya node."""
        return cmds.getAttr('.'.join([self.name, attr]))

    def __setattr__(self, attr, value):
        """
        Set the maya attribute if it exists, else set the python attribute.

        `defaultAttributes` is a list of attributes that are dedicated to python
        and will never be set on the node.
        """
        defaultAttributes = ['name']
        if attr in defaultAttributes:
            super(IcarusNode, self).__setattr__(attr, value)

        attr_name = '.'.join([self.name, attr])

        if cmds.attributeQuery(attr, node=self.name, exists=True):
            cmds.setAttr(attr_name, value)
        else:
            super(IcarusNode, self).__setattr__(attr, value)
