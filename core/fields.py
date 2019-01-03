import maya.cmds as cmds
import json


class Attribute(object):
    def __init__(self, instance, field):
        self.field = field
        self.is_multi = field.create_attr_args.get('multi', False)
        self.attr_name = '.'.join([instance.node_name, field.name])
        if not cmds.attributeQuery(field.name, node=instance.node_name, exists=True):
            cmds.addAttr(
                instance.node_name,
                longName=field.name,
                **field.create_attr_args
            )

    def set(self, value):
        if self.is_multi:
            self._set_multi_attribute(value)
        else:
            self._set_single_attribute(value)

    def get(self):
        if self.is_multi:
            return self._get_multi_attribute()
        else:
            return self.field.cast_from_attr(cmds.getAttr(self.attr_name))

    def _get_multi_attribute(self):
        indices = self._get_multi_indices()
        if indices:
            values = []
            for i in indices:
                val = cmds.getAttr('{}[{}]'.format(self.attr_name, i))
                val = self.field.cast_from_attr(val)
                values.append(val)
            return values
        else:
            return []

    def _set_single_attribute(self, value):
        casted_value = self.field.cast_to_attr(value)
        cmds.setAttr(self.attr_name, casted_value, **self.field.set_attr_args)

    def _set_multi_attribute(self, value):
        self._clear_multi_attribute()
        if not isinstance(value, list):
            value = [value]
        for index, item in enumerate(value):
            casted_item = self.field.cast_to_attr(item)
            attrName = '{}[{}]'.format(self.attr_name, index)
            cmds.setAttr(attrName, casted_item, **self.field.set_attr_args)

    def _clear_multi_attribute(self):
        indices = self._get_multi_indices()
        for index in indices:
            cmds.removeMultiInstance('{}[{}]'.format(self.attr_name, index))

    def _get_multi_indices(self):
        indices = cmds.getAttr(self.attr_name, multiIndices=True)
        if not indices:
            indices = []
        return indices


class FieldContainerMeta(type):
    """Meta class allowing fields to be automatically named.

    Fields class attribute names are collected and assigned to
    the fields as name.
    """

    def __new__(cls, cls_name, bases, attrs):
        fields = []

        for name, attr in attrs.iteritems():
            if isinstance(attr, Field) and attr.name is None:
                attr.name = name
                fields.append(attr)

        attrs['_fields'] = fields
        attrs['_fields_dict'] = {p.name: p for p in fields}
        return type.__new__(cls, cls_name, bases, attrs)


class Field(object):
    create_attr_args = {}
    set_attr_args = {}

    def __init__(
        self,
        **kwargs
    ):
        self.name = None

        # copy the class attribute to the instance
        self.create_attr_args = self.create_attr_args.copy()
        self.create_attr_args.update(kwargs)

        self._attrs = {}

    def __get__(self, instance, instancetype=None):
        self._ensure_maya_attr(instance)
        return self._attrs[instance]

    def _ensure_maya_attr(self, instance):
        if instance not in self._attrs:
            self._attrs[instance] = self.create_attr(instance)

    def create_attr(self, instance):
        return Attribute(instance, self)

    def cast_to_attr(self, value):
        """Cast the received value to a type compatible with maya's attribute.
        """
        return value

    def cast_from_attr(self, value):
        """Cast the received maya's attribute value to a type of your choice.

        See JSONField for an example.
        """
        return value


class IntField(Field):
    create_attr_args = {
        'attributeType': 'long'
    }

    def cast_to_attr(self, value):
        return int(value)


class FloatField(Field):
    create_attr_args = {
        'attributeType': 'double'
    }

    def cast_to_attr(self, value):
        return float(value)


class BoolField(Field):
    create_attr_args = {
        'attributeType': 'bool'
    }

    def cast_to_attr(self, value):
        return bool(value)


class StringField(Field):
    create_attr_args = {
        'dataType': 'string'
    }
    set_attr_args = {
        'type': 'string'
    }

    def cast_to_attr(self, value):
        return str(value)


class JSONField(StringField):
    def cast_to_attr(self, value):
        return json.dumps(value)

    def cast_from_attr(self, value):
        if value is None:
            return None
        return json.loads(value)


class ObjectField(StringField):
    def cast_to_attr(self, value):
        value = super(ObjectField, self).cast_to_attr(value)
        if cmds.objExists(value):
            return value
        else:
            raise ValueError('node `{}` does not exist'.format(value))


class ObjectListField(JSONField):
    def cast_to_attr(self, value):
        if not isinstance(value, (tuple, list)):
            raise ValueError(
                ("{} is an Object List Field and only accepts lists and tuples. "
                 + "provided value was of type {}").format(
                        self.name,
                        type(value),
                )
            )
        curated_objects = []
        for item in value:
            if cmds.objExists(item):
                curated_objects.append(item)
            else:
                raise ValueError(
                    "{} does not exist and can't be added to the field {}".format(
                        item,
                        self.name
                    )
                )
        return json.dumps(curated_objects)

    def cast_from_attr(self, value):
        if value is None:
            return []
        return json.loads(value)

