import collections
import json
import logging

import maya.api.OpenMaya as om2
import maya.cmds as cmds
import maya.mel

from icarus.utils.case import title

logger = logging.getLogger(__name__)


class AttributeBase(object):

    def __init__(self, instance, field):
        self.field = field
        self.is_multi = field.create_attr_args.get('multi', False)
        self.instance = instance
        if not cmds.attributeQuery(field.name, node=instance.node_name, exists=True):
            cmds.addAttr(
                instance.node_name,
                longName=field.name,
                **field.create_attr_args
            )

    @property
    def attr_name(self):
        return '.'.join([self.instance.node_name, self.field.name])


class Attribute(AttributeBase):

    def set(self, value):
        casted_value = self.field.cast_to_attr(value)
        cmds.setAttr(self.attr_name, casted_value, **self.field.set_attr_args)

    def get(self):
        value = cmds.getAttr(self.attr_name, **self.field.get_attr_args)
        return self.field.cast_from_attr(value)


class MessageAttribute(AttributeBase):

    def set(self, value):
        casted_value = self.field.cast_to_attr(value)
        cmds.connectAttr(
            casted_value + '.message',
            self.attr_name,
            force=True,
        )

    def get(self):
        val = cmds.listConnections(
            '{}'.format(self.attr_name),
            source=True,
            shapes=True
        )
        if val:
            return val[0]


class MultiAttribute(AttributeBase, collections.MutableSequence):
    """An interface for Maya multi-attributes."""

    def set(self, value):
        self.clear()
        if not isinstance(value, list):
            value = [value]
        for index, item in enumerate(value):
            casted_item = self.field.cast_to_attr(item)
            attrName = '{}[{}]'.format(self.attr_name, index)
            cmds.setAttr(attrName, casted_item, **self.field.set_attr_args)

    def get(self):
        values = []
        for val in cmds.getAttr('{}[*]'.format(self.attr_name)):
            val = self.field.cast_from_attr(val)
            values.append(val)
        return values

    def clear(self):
        try:
            cmds.removeMultiInstance(
                self.attr_name,
                allChildren=True,
                b=True
            )
        except RuntimeError:
            pass

    def __getitem__(self, index):
        val = cmds.getAttr('{}[{}]'.format(self.attr_name, self._logical_index(index)))
        return self.field.cast_from_attr(val)

    def __setitem__(self, index, value):
        casted_item = self.field.cast_to_attr(value)
        attrName = '{}[{}]'.format(self.attr_name, self._logical_index(index))
        cmds.setAttr(attrName, casted_item, **self.field.set_attr_args)

    def __delitem__(self, index):
        target = '{}[{}]'.format(self.attr_name, self._logical_index(index))
        sources = cmds.listConnections(
            target,
            source=True,
            plugs=True
        ) or []

        for source in sources:
            cmds.disconnectAttr(source, target)

        cmds.removeMultiInstance(
            target,
            b=True
        )

    def __len__(self):
        return len(cmds.getAttr('{}[*]'.format(self.attr_name)))

    def insert(self, index, value):
        casted_item = self.field.cast_to_attr(value)
        attrName = '{}[{}]'.format(self.attr_name, index)
        cmds.setAttr(attrName, casted_item, **self.field.set_attr_args)

    def append(self, value):
        """Append to the very last plug of the multi attribute."""
        index = cmds.getAttr('{}'.format(self.attr_name), size=True)
        self.insert(index, value)

    def _logical_indices(self):
        sel = om2.MSelectionList()
        node_name, _, plug_name = self.attr_name.partition('.')
        sel.add(node_name)
        mobj = sel.getDependNode(0)
        mfn = om2.MFnDependencyNode(mobj)
        plug = mfn.findPlug(plug_name, 0)
        return plug.getExistingArrayAttributeIndices()

    def _logical_index(self, index):
        logical_indices = self._logical_indices()
        if logical_indices:
            try:
                return logical_indices[index]
            except IndexError:
                return max(logical_indices) + 1
        else:
            return 0


class MessageMultiAttribute(MultiAttribute):

    def __setitem__(self, index, value):
        casted_item = self.field.cast_to_attr(value)
        attrName = '{}[{}]'.format(self.attr_name, index)
        cmds.connectAttr(casted_item + '.message', attrName)

    def get(self):
        values = cmds.listConnections(
            '{}'.format(self.attr_name),
            source=True
        ) or []
        return map(self.field.cast_from_attr, values)

    def set(self, value):
        self.clear()
        if not isinstance(value, list):
            value = [value]
        for index, item in enumerate(value):
            casted_item = self.field.cast_to_attr(item)
            attrName = '{}[{}]'.format(self.attr_name, index)
            cmds.connectAttr(casted_item + '.message', attrName)

    def __getitem__(self, index):
        # not using logical indices since listConnections only returns
        # existing connections
        val = cmds.listConnections(
            '{}'.format(self.attr_name),
            source=True
        ) or []
        return self.field.cast_from_attr(val[index])

    def __len__(self):
        return len(cmds.listConnections(
            '{}'.format(self.attr_name),
            source=True) or []
        )

    def insert(self, index, value):
        casted_item = self.field.cast_to_attr(value)
        attrName = '{}[{}]'.format(self.attr_name, index)
        cmds.connectAttr(casted_item + '.message', attrName)


class FieldContainerMeta(type):
    """Meta class allowing fields to be automatically named.

    Fields class attribute names are collected and assigned to
    the fields as name.
    """

    def __new__(cls, cls_name, bases, attrs):
        fields = []

        parent_classes = []
        for base in bases:
            parent_classes.append(base)
            for parent in base.__mro__:
                parent_classes.append(parent)

        for name, attr in attrs.iteritems():
            if isinstance(attr, Field) and attr.name is None:
                attr.name = name
                if attr.display_name is None:
                    attr.display_name = title(name)
                if attr not in fields:
                    fields.append(attr)

        for parent in parent_classes:
            for name, attr in parent.__dict__.iteritems():
                if isinstance(attr, Field):
                    field_names = [n.name for n in fields]
                    if attr.name not in field_names:
                        fields.append(attr)

        attrs['fields'] = fields
        attrs['fields_dict'] = {p.name: p for p in fields}
        return type.__new__(cls, cls_name, bases, attrs)


class Field(object):
    create_attr_args = {}
    set_attr_args = {}
    get_attr_args = {}

    def __init__(
        self,
        **kwargs
    ):
        self.name = None
        self.displayable = kwargs.pop('displayable', False)
        self.editable = kwargs.pop('editable', False)
        self.display_name = kwargs.pop('display_name', None)
        self.gui_order = kwargs.pop('gui_order', 1)
        self.unique = kwargs.pop('unique', False)

        # copy the class attribute to the instance
        self.create_attr_args = self.create_attr_args.copy()
        self.create_attr_args.update(kwargs)

        self._attrs = {}

    def __get__(self, instance, instancetype=None):
        self.ensure_maya_attr(instance)
        return self._attrs[instance]

    def ensure_maya_attr(self, instance):
        if instance not in self._attrs:
            self._attrs[instance] = self.create_attr(instance)

    def create_attr(self, instance):
        if self.create_attr_args.get('multi', False):
            return MultiAttribute(instance, self)
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

    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.get('minValue', None)
        self.max_value = kwargs.get('maxValue', None)
        super(IntField, self).__init__(*args, **kwargs)

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


class EnumField(Field):
    """A field for enum values.

    You can set the enum values using the ``choices`` argument.

    This argument must be a list of strings.
    """
    create_attr_args = {
        'attributeType': 'enum'
    }
    get_attr_args = {
        'asString': True
    }
    
    def __init__(self, **kwargs):
        self.choices = kwargs.pop('choices', [])
        super(EnumField, self).__init__(**kwargs)
        self.create_attr_args['enumName'] = ':'.join(self.choices)

    def cast_to_attr(self, value):
        """Cast to the :class:`int` value of ``value``.

        :param value: Enum name to set.
        :type value: str
        :rtype: int
        """
        return self.choices.index(value)


class JSONField(StringField):
    def cast_to_attr(self, value):
        return json.dumps(value)

    def cast_from_attr(self, value):
        if value is None:
            return None
        return json.loads(value)


class ObjectField(StringField):
    create_attr_args = {
        'attributeType': 'message',
    }

    def create_attr(self, instance):
        return MessageAttribute(instance, self)

    def cast_to_attr(self, value):
        value = super(ObjectField, self).cast_to_attr(value)
        if cmds.objExists(value):
            return value
        else:
            raise ValueError('node `{}` does not exist'.format(value))


class ObjectListField(Field):
    create_attr_args = {
        'attributeType': 'message',
        'multi': True
    }

    def create_attr(self, instance):
        return MessageMultiAttribute(instance, self)

    def cast_to_attr(self, value):
        return str(value)
