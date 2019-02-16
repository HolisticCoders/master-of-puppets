from operator import attrgetter
from weakref import WeakValueDictionary

from icarus.vendor.Qt import QtCore, QtWidgets
from icarus.ui.signals import publish, subscribe
from icarus.ui.utils import clear_layout
from icarus.ui.fieldwidgets import map_field_to_widget
from icarus.core.rig import Rig


class ModulePanel(QtWidgets.QDockWidget):

    def __init__(self, parent=None):
        super(ModulePanel, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName('icarus_settings_panel')
        self.setWindowTitle('Module Panel')

        self._module_widgets = WeakValueDictionary()

        self.setWidget(QtWidgets.QWidget())

        layout = QtWidgets.QVBoxLayout()
        self.widget().setLayout(layout)

        self.settings_group = QtWidgets.QGroupBox('Settings')
        self.form = QtWidgets.QFormLayout()
        self.apply_button = QtWidgets.QPushButton('Apply')

        self.actions_group = QtWidgets.QGroupBox('Actions')
        self.delete_button = QtWidgets.QPushButton('Delete')

        layout.addWidget(self.settings_group)
        layout.addStretch()
        layout.addWidget(self.actions_group)

        settings_layout = QtWidgets.QVBoxLayout()
        self.settings_group.setLayout(settings_layout)
        settings_layout.addLayout(self.form)
        settings_layout.addWidget(self.apply_button)

        actions_layout = QtWidgets.QVBoxLayout()
        self.actions_group.setLayout(actions_layout)
        actions_layout.addWidget(self.delete_button)

        self.apply_button.released.connect(self._update_module)
        self.apply_button.hide()
        self.delete_button.released.connect(self._delete_module)
        self.delete_button.hide()

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

    def _update_module(self):
        """Update the Maya module."""
        if not self.modules:
            return
        for module in self.modules:
            for name, widget in self._module_widgets.iteritems():
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

    def _update_ui(self):
        clear_layout(self.form)
        if not self.modules:
            self.apply_button.hide()
            self.delete_button.hide()
            return

        # If one of the module is built, disable actions.
        is_built = False
        for module in self.modules:
            if module.is_built.get():
                is_built = True
        
        if is_built:
            self.apply_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        else:
            self.apply_button.setEnabled(True)
            self.delete_button.setEnabled(True)

        self.apply_button.show()
        self.delete_button.show()

        # Only show fields shared by all selected modules.
        field_names = set([f.name for f in self.modules[-1].fields])
        for other in self.modules[:-1]:
            other_names = set([f.name for f in other.fields])
            field_names = field_names.intersection(other_names)

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
            value = getattr(self.modules[-1], field.name).get()
            widget.set(value)

            self._module_widgets[field.name] = widget

            self.form.addRow(field.display_name, widget)

            if not field.editable or is_built:
                widget.setEnabled(False)
