from urllib.parse import urlencode
from collections import OrderedDict
from datetime import datetime

import math

from django import template

register = template.Library()


@register.simple_tag
def url_replace(request, field, value, direction=""):
    # Taken from https://stackoverflow.com/questions/2272370/sortable-table-columns-in-django
    dict_ = request.GET.copy()

    if field == "order_by" and field in dict_.keys():
        if dict_[field].startswith("-") and dict_[field].lstrip("-") == value:
            dict_[field] = value
        elif dict_[field].lstrip("-") == value:
            dict_[field] = "-" + value
        else:
            dict_[field] = direction + value
    else:
        dict_[field] = direction + value

    return urlencode(OrderedDict(sorted(dict_.items())))


@register.simple_tag
def get_type_count(dictionary, key):
    # Taken from
    # https://stackoverflow.com/questions/50703556/get-dictionary-value-by-key-in-django-template
    # And edited for attributes
    # Grab the count got the key type but changing the attributes to a dictionary
    return dictionary.__dict__.get(key + "_count")


@register.filter
def is_not_nan_or_none(value):
    return not math.isnan(value) or not value is None


@register.filter
def get_attr(obj, attr_name):
    return getattr(obj, attr_name, None)


@register.filter
def isoformat(value: datetime):
    """To return the iso date format from a Django datetime field."""
    return value.isoformat()  # 'c' is the format string for ISO 8601 in Django


@register.filter
def get_label_mapping(value, mapping):
    return mapping.get(value, value)
