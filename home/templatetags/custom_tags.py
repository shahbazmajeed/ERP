# your_app/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def dict_get(dict_list, key):
    """Convert list of tuples to dict and get value for key"""
    return dict(dict_list).get(key, '')

@register.filter(name='upper')
def upper(value):
    """Convert a string to uppercase"""
    return value.upper()
