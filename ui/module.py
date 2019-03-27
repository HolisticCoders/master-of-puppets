from functools import partial
from operator import attrgetter
from weakref import WeakValueDictionary

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from icarus.vendor.Qt import QtCore, QtWidgets
from icarus.ui.signals import publish, subscribe
from icarus.ui.utils import clear_layout
from icarus.ui.fieldwidgets import map_field_to_widget
from icarus.core.rig import Rig
import icarus.metadata
from icarus.core.fields import ObjectField, ObjectListField


class ModulePanel(QtWidgets.QDockWidget):

    def __init__(self, parent=None):
        super(ModulePanel, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName('icarus_settings_panel')
        self.setWindowTitle('Module Panel')

        self._module_widgets = WeakValueDictionary()
        self._modified_fields = set()
        self._initial_values = {}

        self.setWidget(QtWidgets.QWidget())

        self.settings_group = QtWidgets.QGroupBox('Settings')
        self.form = QtWidgets.QFormLayout()
        self.apply_button = QtWidgets.QPushButton('Apply')
        self.reset_button = QtWidgets.QPushButton('Reset')

        self.actions_group = QtWidgets.QGroupBox('Actions')
        self.mirror_button = QtWidgets.QPushButton('Mirror')
        self.duplicate_button = QtWidgets.QPushButton('Duplicate')
        self.delete_button = QtWidgets.QPushButton('Delete')

        layout = QtWidgets.QVBoxLayout()
        self.widget().setLayout(layout)

        layout.addWidget(self.settings_group)
        layout.addStretch()
        layout.addWidget(self.actions_group)

        settings_layout = QtWidgets.QVBoxLayout()
        self.settings_group.setLayout(settings_layout)
        settings_layout.addLayout(self.form)

        settings_actions_layout = QtWidgets.QHBoxLayout()
        settings_layout.addLayout(settings_actions_layout)

        settings_actions_layout.addWidget(self.apply_button)
        settings_actions_layout.addWidget(self.reset_button)

        actions_layout = QtWidgets.QVBoxLayout()
        self.actions_group.setLayout(actions_layout)
        actions_layout.addWidget(self.mirror_button)
        actions_layout.addWidget(self.duplicate_button)
        actions_layout.addWidget(self.delete_button)

        self.apply_button.hide()
        self.reset_button.hide()
        self.mirror_button.hide()
        self.duplicate_button.hide()
        self.delete_button.hide()

        self.apply_button.released.connect(self._update_module)
        self.reset_button.released.connect(self._update_ui)
        self.mirror_button.released.connect(self._mirror_module)
        self.duplicate_button.released.connect(self._duplicate_module)
        self.delete_button.released.connect(self._delete_module)

        subscribe('selected-modules-changed', self._on_selection_changed)

    def _on_selection_changed(self, modules):
        """Update the module to edit.

        ``modules`` argument is a :class:`list` of
        :class:`icarus.core.module.RigModule` and/or :class:`str`
        instances.

        :param pointer: Data to the selected module.
                        It is a list of modules and/or joints.
        :type pointer: list
        """

        def is_module(module):
            return not isinstance(module, basestring)

        self.modules = filter(is_module, modules)
        self._update_ui()

    def _on_field_edited(self, widget, *args):
        label = self.form.labelForField(widget)
        if widget.get() != self._initial_values[widget]:
            self._modified_fields.add(widget)
            label.setStyleSheet('font-weight: bold')
        else:
            self._modified_fields.remove(widget)
            label.setStyleSheet('')

        if self._modified_fields:
            self.apply_button.setEnabled(True)
            self.reset_button.setEnabled(True)
        else:
            self.apply_button.setEnabled(False)
            self.reset_button.setEnabled(False)

    def _update_module(self):
        """Update the Maya module."""
        if not self.modules:
            return
        for module in self.modules:
            for name, widget in self._module_widgets.iteritems():
                if widget not in self._modified_fields:
                    continue
                field = getattr(module, name)
                value = widget.get()
                field.set(value)
            module.update()
        publish('modules-updated', self.modules)

    def _delete_module(self):
        """Delete the selected module."""
        if not self.modules:
            return
        button = QtWidgets.QMessageBox.warning(
            self,
            'Icarus - Delete Module',
            'You are about to delete %d module(s). Continue ?' % len(self.modules),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if button != QtWidgets.QMessageBox.Yes:
            return
        rig = Rig()
        for module in self.modules:
            rig.delete_module(module.node_name)
        publish('modules-deleted', self.modules)

    def _duplicate_module(self):
        """Duplicate the selected module."""
        if not self.modules:
            return
        rig = Rig()
        new_modules = []
        for module in self.modules:
            new_module = rig.duplicate(module)
            new_modules.append(new_module)

        publish('modules-created', new_modules)

    def _mirror_module(self):
        cmds.undoInfo(openChunk=True)
        if not self.modules:
            return
        rig = Rig()
        new_modules = []
        for module in self.modules:
            orig_side = module.side.get()
            if orig_side == 'M':
                continue
            new_side = 'R' if orig_side == 'L' else 'L'
            orig_name = module.name.get()
            orig_type = module.module_type.get()
            mirror_type = module.mirror_type.get()

            orig_parent_joint = module.parent_joint.get()
            metadata = icarus.metadata.metadata_from_name(orig_parent_joint)
            metadata['side'] = new_side
            new_parent_joint = icarus.metadata.name_from_metadata(metadata)
            if not cmds.objExists(new_parent_joint):
                new_parent_joint = orig_parent_joint

            new_module = rig.add_module(
                orig_type,
                name=orig_name,
                side=new_side,
                parent_joint=new_parent_joint
            )
            new_modules.append(new_module)

            for field in module.fields:
                if field.name in ['name', 'side']:
                    continue
                if isinstance(field, ObjectField) or isinstance(field, ObjectListField):
                    continue
                if field.editable:
                    value = getattr(module, field.name).get()
                    getattr(new_module, field.name).set(value)
            new_module.update()
            module._mirror_module.set(new_module.node_name)
            new_module._mirror_module.set(module.node_name)

            # actually mirror the nodes
            orig_nodes = module.deform_joints.get() + module.placement_locators.get()
            new_nodes = new_module.deform_joints.get() + new_module.placement_locators.get()
            for orig_node, new_node in zip(orig_nodes, new_nodes):
                if mirror_type.lower() == 'behavior':
                    world_reflexion_mat = om2.MMatrix([
                        -1.0, -0.0, -0.0, 0.0,
                         0.0,  1.0,  0.0, 0.0,
                         0.0,  0.0,  1.0, 0.0,
                         0.0,  0.0,  0.0, 1.0
                    ])
                    local_reflexion_mat = om2.MMatrix([
                        -1.0,  0.0,  0.0, 0.0,
                         0.0, -1.0,  0.0, 0.0,
                         0.0,  0.0, -1.0, 0.0,
                         0.0,  0.0,  0.0, 1.0
                    ])
                    orig_node_mat = om2.MMatrix(
                        cmds.getAttr(orig_node + '.worldMatrix')
                    )
                    new_node_parent = cmds.listRelatives(new_node, parent=True)
                    new_mat = local_reflexion_mat * orig_node_mat * world_reflexion_mat
                    cmds.xform(new_node, matrix=new_mat, worldSpace=True)
                    cmds.setAttr(new_node + '.scale', 1, 1, 1)
                if mirror_type.lower() == 'orientation':
                    world_reflexion_mat = om2.MMatrix([
                        -1.0, -0.0, -0.0, 0.0,
                         0.0,  1.0,  0.0, 0.0,
                         0.0,  0.0,  1.0, 0.0,
                         0.0,  0.0,  0.0, 1.0
                    ])
                    orig_node_mat = om2.MMatrix(
                        cmds.getAttr(orig_node + '.worldMatrix')
                    )
                    new_node_parent = cmds.listRelatives(new_node, parent=True)
                    new_mat = orig_node_mat * world_reflexion_mat
                    cmds.xform(new_node, matrix=new_mat, worldSpace=True)
                    cmds.setAttr(new_node + '.scale', 1, 1, 1)
                    orig_orient = cmds.xform(orig_node, q=True, rotation=True, ws=True)
                    cmds.xform(new_node, rotation=orig_orient, ws=True)

        # mirror the object fields and object list fields values
        for module, new_module in zip(self.modules, new_modules):
            orig_side = module.side.get()
            for field in module.fields:
                if field.editable:
                    if isinstance(field, ObjectField):
                        orig_value = getattr(module, field.name).get()
                        if orig_side == 'M':
                            value = orig_value
                        else:
                            new_side = 'R' if orig_side == 'L' else 'L'
                            metadata = icarus.metadata.metadata_from_name(orig_value)
                            metadata['side'] = new_side
                            new_name = icarus.metadata.name_from_metadata(metadata)
                            if cmds.objExists(new_name):
                                value = new_name
                            else:
                                value = orig_value
                    elif isinstance(field, ObjectListField):
                        orig_value = getattr(module, field.name).get()
                        value = []
                        for val in orig_value:
                            if orig_side == 'M':
                                value.append(orig_value)
                            else:
                                new_side = 'R' if orig_side == 'L' else 'L'
                                metadata = icarus.metadata.metadata_from_name(orig_value)
                                metadata['side'] = new_side
                                new_name = icarus.metadata.name_from_metadata(metadata)
                                if cmds.objExists(new_name):
                                    value.append(new_name)
                                else:
                                    value.append(orig_value)
                    else:
                        continue

                    getattr(new_module, field.name).set(value)
            new_module.update()

        cmds.undoInfo(closeChunk=True)
        publish('modules-created', new_modules)

    def _update_ui(self):
        self._modified_fields = set()
        self._initial_values = {}
        clear_layout(self.form)
        if not self.modules:
            self.apply_button.hide()
            self.reset_button.hide()
            self.mirror_button.hide()
            self.duplicate_button.hide()
            self.delete_button.hide()
            return

        # If one of the module is built, disable actions.
        is_built = False
        for module in self.modules:
            if module.is_built.get():
                is_built = True

        if is_built:
            self.mirror_button.setEnabled(False)
            self.duplicate_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.mirror_button.setEnabled(True)
            self.duplicate_button.setEnabled(True)
            self.delete_button.setEnabled(True)

        # Enable apply and reset button only when a field has
        # been modified.
        self.apply_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.apply_button.show()
        self.reset_button.show()
        self.mirror_button.show()
        self.duplicate_button.show()
        self.delete_button.show()

        # Only show fields shared by all selected modules.
        field_names = set([f.name for f in self.modules[-1].fields])
        for other in self.modules[:-1]:
            other_names = set([f.name for f in other.fields])
            field_names = field_names.intersection(other_names)

        # Filter out fields that must be unique, so users cannot
        # edit them on multiple modules at once.
        for field in self.modules[-1].fields:
            if not field.unique:
                continue
            if field.name in field_names and len(self.modules) > 1:
                field_names.remove(field.name)

        fields = [f for f in self.modules[-1].fields if f.name in field_names]
        ordered_fields = sorted(
            fields,
            key=attrgetter('gui_order')
        )
        for field in ordered_fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name,
                map_field_to_widget['StringField']
            )
            widget = widget_data(field)
            if field.tooltip:
                widget.setToolTip(field.tooltip)
            value = getattr(self.modules[-1], field.name).get()
            widget.set(value)
            self._initial_values[widget] = value

            self._module_widgets[field.name] = widget
            widget.signal().connect(partial(self._on_field_edited, widget))

            self.form.addRow(field.display_name, widget)

            if not field.editable or is_built:
                widget.setEnabled(False)
