from django import template

register = template.Library()

@register.filter
def dividedby(value, arg):
    """Divides the value by the argument and returns an integer result."""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0
