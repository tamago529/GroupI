from django import template

register = template.Library()

@register.filter
def get_item(d: dict, key):
    return d.get(key) if d else None
