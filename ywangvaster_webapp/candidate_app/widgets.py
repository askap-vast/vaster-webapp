from django.forms.widgets import MultiWidget, TextInput
from django.utils.safestring import mark_safe


class RangeSliderWidget(MultiWidget):
    template_name = "widgets/range_slider.html"

    def __init__(self, attrs=None):
        widgets = {
            "0": TextInput(attrs={"type": "range", "min": "0", "max": "100", "id": "rangeSlider"}),
            "1": TextInput(attrs={"type": "hidden", "id": "minValue"}),
            "2": TextInput(attrs={"type": "hidden", "id": "maxValue"}),
        }
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(",")
        return [None, None]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["subwidgets"] = self.subwidgets(value, attrs)

        return context
