import maya.cmds as cmds


class Attribute(object):
    def __init__(self, instance, field):
        self.field = field
        self.attr_name = '.'.join([instance.name, field.name])
        if not cmds.attributeQuery(field.name, node=instance.name, exists=True):
            cmds.addAttr(
                instance.name,
                longName=field.name,
                **field.create_attr_args
            )

    def set(self, value):
        casted_value = self.field.cast(value)
        cmds.setAttr(self.attr_name, casted_value, **self.field.set_attr_args)

    def get(self):
        return cmds.getAttr(self.attr_name)


class Field(object):
    create_attr_args = {}
    set_attr_args = {}

    def __init__(
        self,
        name=None,
        as_list=False,
    ):
        self.name = name
        if as_list:
            self.create_attr_args['multi'] = True
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
    create_attr_args = {
        'attributeType': 'long'
    }

    def cast(self, value):
        return int(value)

class FloatField(Field):
    create_attr_args = {
        'attributeType': 'double'
    }

    def cast(self, value):
        return float(value)

class BoolField(Field):
    create_attr_args = {
        'attributeType': 'bool'
    }

    def cast(self, value):
        return bool(value)

class StringField(Field):
    create_attr_args = {
        'dataType': 'string'
    }
    set_attr_args = {
        'type': 'string'
    }

    def cast(self, value):
        return str(value)

class ObjectField(StringField):
    def cast(self, value):
        value = super(ObjectField, self).cast(value)
        if cmds.objExists(value):
            return value
        else:
            raise ValueError('node `{}` does not exist'.format(value))
