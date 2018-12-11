import maya.cmds as cmds

class Attribute(object):
    def __init__(self, instance, field):
        self.node = instance
        self.attr_name = '.'.join([self.node.name, field.name])
        if not cmds.attributeQuery(field.name, node=self.node.name, exists=True):
            cmds.addAttr(
                self.instance.name,
                longName=field.name,
                attributeType=field.attr_type,
            )

    def set(self, value):
        cmds.setAttr(self.attr_name, value)

    def get(self):
        return cmds.getAttr(self.attr_name)

class Field(object):
    def __init__(
        self,
        name=None,
    ):
        self.name = name
        self._attrs = {}

    def __get__(self, instance, instancetype=None):
        self._ensure_maya_attr(instance)
        return self._attrs[instance]

    def _ensure_maya_attr(self, instance):
        if instance not in self._attrs:
            self._attrs[instance] = self.create_attr(instance)

    def create_attr(self, instance):
        return Attribute(instance, self)

class IntField(Field):
    attr_type = 'long'

