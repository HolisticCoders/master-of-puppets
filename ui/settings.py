from functools import partial

from icarus.vendor.Qt import QtWidgets
from icarus.modules.chain import Chain
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
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        module = Chain('chain_M_mod')

        for field in module.fields:
            if not field.displayable:
                continue

            class_name = field.__class__.__name__
            widget_data = map_field_to_widget.get(
                class_name,
                map_field_to_widget['StringField']
            )
            widget = widget_data(field)
            value = getattr(module, field.name).get()
            widget.set(value)

            widget.signal().connect(
                partial(self._update_field, field, module)
            )

            form.addRow(field.display_name, widget)

            if not field.editable:
                widget.setEnabled(False)

    def _update_field(self, field, module, value):
        getattr(module, field.name).set(value)

        module = Chain('chain_M_mod')
        module.update()

