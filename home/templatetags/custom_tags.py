from django import template
register = template.Library()

@register.filter
def dict_get(dict_list, key):
    return dict(dict_list).get(key, '')
