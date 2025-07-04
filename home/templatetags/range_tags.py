# home/templatetags/range_tags.py
from django import template

register = template.Library()

@register.filter
def to(value, end):
    return range(value, end)
