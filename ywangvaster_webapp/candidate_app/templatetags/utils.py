from urllib.parse import urlencode
from collections import OrderedDict

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
