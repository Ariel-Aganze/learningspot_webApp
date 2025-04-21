from django import template
register = template.Library()

@register.filter
def get(dictionary, key):
    """Gets an item from a dictionary using a key."""
    if dictionary is None:
        return None
    # Convert to integer if key is a string containing just digits
    if isinstance(key, str) and key.isdigit():
        key = int(key)
    return dictionary.get(key)