"""Qt widgets for Icarus fields."""
from icarus.vendor.Qt import QtWidgets


class SpinBox(QtWidgets.QSpinBox):
    def __init__(self, field, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
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
        return self.value()

    def set(self, value):
        self.setValue(value)

    def signal(self):
        return self.valueChanged


class LineEdit(QtWidgets.QLineEdit):
    def __init__(self, field, *args, **kwargs):
        super(LineEdit, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setText(value)

    def get(self):
        return self.text()

    def signal(self):
        return self.textChanged


class CheckBox(QtWidgets.QCheckBox):
    def __init__(self, field, *args, **kwargs):
        super(CheckBox, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setChecked(value)

    def get(self):
        return self.isChecked()

    def signal(self):
        return self.stateChanged


map_field_to_widget = {
    'BoolField': CheckBox,
    'IntField': SpinBox,
    'StringField': LineEdit,
    'ObjectField': LineEdit,
}
