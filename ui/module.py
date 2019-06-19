import logging
from collections import defaultdict
from functools import partial
from operator import attrgetter
from weakref import WeakValueDictionary

import maya.cmds as cmds
import maya.api.OpenMaya as om2

from mop.vendor.Qt import QtCore, QtWidgets
from mop.ui.signals import publish, subscribe
from mop.ui.utils import clear_layout
from mop.utils.undo import undoable
from mop.ui.fieldwidgets import map_field_to_widget
from mop.core.rig import Rig
import mop.metadata
from mop.core.fields import ObjectField, ObjectListField

logger = logging.getLogger(__name__)


class ModulePanel(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super(ModulePanel, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName("mop_settings_panel")
        self.setWindowTitle("Module Panel")

        self._module_widgets = WeakValueDictionary()
        self._modified_fields = set()
        self._initial_values = {}

        self.setWidget(QtWidgets.QWidget())

        self.settings_group = QtWidgets.QGroupBox("Settings")
        self.form = QtWidgets.QFormLayout()
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.reset_button = QtWidgets.QPushButton("Reset")

        self.actions_group = QtWidgets.QGroupBox("Actions")
        self.mirror_button = QtWidgets.QPushButton("Mirror")
        self.update_mirror_button = QtWidgets.QPushButton("Update Mirror")
        self.duplicate_button = QtWidgets.QPushButton("Duplicate")
        self.delete_button = QtWidgets.QPushButton("Delete")

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
        actions_layout.addWidget(self.update_mirror_button)
        actions_layout.addWidget(self.duplicate_button)
        actions_layout.addWidget(self.delete_button)

        self.apply_button.hide()
        self.reset_button.hide()
        self.mirror_button.hide()
        self.update_mirror_button.hide()
        self.duplicate_button.hide()
        self.delete_button.hide()

        self.apply_button.released.connect(self._update_module)
        self.reset_button.released.connect(self._update_ui)
        self.mirror_button.released.connect(self._mirror_module)
        self.update_mirror_button.released.connect(self._update_mirror)
        self.duplicate_button.released.connect(self._duplicate_module)
        self.delete_button.released.connect(self._delete_module)

        subscribe("selected-modules-changed", self._on_selection_changed)

    def _on_selection_changed(self, modules):
        """Update the module to edit.

        ``modules`` argument is a :class:`list` of
        :class:`mop.core.module.RigModule` and/or :class:`str`
        instances.

        :param pointer: Data to the selected module.
                        It is a list of modules and/or joints.
        :type pointer: list
        """

        def is_module(module):
            return not isinstance(module, basestring) and cmds.objExists(
                module.node_name
            )

        self.modules = filter(is_module, modules)
        self._update_ui()

    def _on_field_edited(self, widget, *args):
        label = self.form.labelForField(widget)
        if widget.get() != self._initial_values[widget]:
            self._modified_fields.add(widget)
            label.setStyleSheet("font-weight: bold")
        else:
            self._modified_fields.remove(widget)
            label.setStyleSheet("")

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

        modified_fields = defaultdict(dict)
        for module in self.modules:
            old_name = module.node_name
            for name, widget in self._module_widgets.iteritems():
                if widget not in self._modified_fields:
                    continue
                field = getattr(module, name)
                old_value = field.get()
                value = widget.get()
                field.set(value)
                label = self.form.labelForField(widget)
                label.setStyleSheet("")
                self._initial_values[widget] = value
                modified_fields[module][name] = (old_value, value)
            module.update()
            new_name = module.node_name
            if new_name != old_name:
                modified_fields[module]["node_name"] = (old_name, new_name)

        self.apply_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self._modified_fields.clear()

        publish("modules-updated", modified_fields)

    def _delete_module(self):
        """Delete the selected module."""
        if not self.modules:
            return
        button = QtWidgets.QMessageBox.warning(
            self,
            "mop - Delete Module",
            "You are about to delete %d module(s). Continue ?" % len(self.modules),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if button != QtWidgets.QMessageBox.Yes:
            return
        rig = Rig()
        modules = self.modules[:]
        for module in self.modules:
            if module.name.get() == "root":
                logger.warning("Cannot delete root module.")
                modules.remove(module)
                continue
            rig.delete_module(module.node_name)
        publish("modules-deleted", modules)

    def _duplicate_module(self):
        """Duplicate the selected module."""
        if not self.modules:
            return
        rig = Rig()
        new_modules = []
        for module in self.modules:
            new_module = rig.duplicate_module(module)
            new_modules.append(new_module)

        publish("modules-created", new_modules)

    @undoable
    def _mirror_module(self):
        if not self.modules:
            return
        rig = Rig()
        new_modules = []
        for module in self.modules:
            new_module = rig.mirror_module(module)
            if new_module is not None:
                new_modules.append(new_module)

        publish("modules-created", new_modules)

    @undoable
    def _update_mirror(self):
        if not self.modules:
            return
        for module in self.modules:
            mirror_mod = module.module_mirror
            if not mirror_mod:
                continue
            if mirror_mod in self.modules:
                self.modules.remove(mirror_mod)
            module.update_mirror()

    def _update_ui(self):
        self._modified_fields.clear()
        self._initial_values.clear()
        clear_layout(self.form)
        if not self.modules:
            self.apply_button.hide()
            self.reset_button.hide()
            self.mirror_button.hide()
            self.update_mirror_button.hide()
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
            self.update_mirror_button.setEnabled(False)
            self.duplicate_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.mirror_button.setEnabled(True)
            self.update_mirror_button.setEnabled(True)
            self.duplicate_button.setEnabled(True)
            self.delete_button.setEnabled(True)

        # Enable apply and reset button only when a field has
        # been modified.
        self.apply_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.apply_button.show()
        self.reset_button.show()
        self.mirror_button.show()
        self.update_mirror_button.show()
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
        ordered_fields = sorted(fields, key=attrgetter("gui_order"))
        for field in ordered_fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name, map_field_to_widget["StringField"]
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
