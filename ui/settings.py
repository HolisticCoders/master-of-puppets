from functools import partial
from operator import attrgetter

from icarus.vendor.Qt import QtWidgets
from icarus.core.rig import Rig
from icarus.ui.signals import observe
from icarus.ui.utils import clear_layout
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class ISpinBox(QtWidgets.QSpinBox):
    def __init__(self, field, *args, **kwargs):
        super(ISpinBox, self).__init__(*args, **kwargs)
        self.field = field
        minValue = field.min_value
        maxValue = field.max_value
        if minValue is not None:
            self.setMinimum(minValue)
        else:
            self.setMinimum(-1000000)
        if maxValue is not None:
            self.setMaximum(maxValue)
        else:
            self.setMaximum(1000000)

    def get(self):
        self.value()

    def set(self, value):
        self.setValue(value)

    def signal(self):
        return self.valueChanged


class ILineEdit(QtWidgets.QLineEdit):
    def __init__(self, field, *args, **kwargs):
        super(ILineEdit, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setText(value)

    def get(self):
        self.text()

    def signal(self):
        return self.textChanged


class ICheckBox(QtWidgets.QCheckBox):
    def __init__(self, field, *args, **kwargs):
        super(ICheckBox, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setChecked(value)

    def get(self):
        self.isChecked()

    def signal(self):
        return self.stateChanged


map_field_to_widget = {
    'BoolField': ICheckBox,
    'IntField': ISpinBox,
    'StringField': ILineEdit,
    'ObjectField': ILineEdit,
}


class SettingsPanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(SettingsPanel, self).__init__(parent)
        self.setWindowTitle('Icarus Settings')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.form = QtWidgets.QFormLayout()
        layout.addLayout(self.form)

        observe('selected-module-changed', self._on_module_selected)

    def _update_field(self, field, value):
        getattr(self.module, field.name).set(value)
        self.module.update()

    def _on_module_selected(self, module):
        """Update the module to edit."""
        self.module = module
        self._update_ui()

    def _update_ui(self):
        clear_layout(self.form)
        if not self.module:
            return
        ordered_fields = sorted(self.module.fields, key=attrgetter('gui_order'))
        for field in ordered_fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name,
                map_field_to_widget['StringField']
            )
            widget = widget_data(field)
            value = getattr(self.module, field.name).get()
            widget.set(value)

            widget.signal().connect(
                partial(self._update_field, field)
            )

            self.form.addRow(field.display_name, widget)

            if not field.editable:
                widget.setEnabled(False)
