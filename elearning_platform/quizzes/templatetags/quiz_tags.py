from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    """
    Get an item from a dictionary using its key.
    Usage: {{ dictionary|get:key }}
    """
    if dictionary is None:
        return None
    
    # Convert to integer if key is a string of digits
    if isinstance(key, str) and key.isdigit():
        key = int(key)
    
    return dictionary.get(key)

@register.filter
def format_time(seconds):
    """
    Format time in seconds to MM:SS format.
    Usage: {{ 65|format_time }} -> "1:05"
    """
    if seconds is None:
        return "0:00"
    
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

@register.filter
def question_type_icon(question_type):
    """
    Return an appropriate Bootstrap icon class for a question type.
    Usage: {{ question.question_type|question_type_icon }}
    """
    icons = {
        'multiple_choice': 'bi-list-check',
        'multi_select': 'bi-check-all',
        'true_false': 'bi-toggle-on',
        'dropdown': 'bi-caret-down-square',
        'star_rating': 'bi-star',
        'likert_scale': 'bi-bar-chart',
        'matrix': 'bi-grid-3x3',
        'image_choice': 'bi-image',
        'image_rating': 'bi-star-half',
        'short_answer': 'bi-pencil',
        'long_answer': 'bi-textarea-t',
        'file_upload': 'bi-file-earmark-arrow-up',
        'voice_record': 'bi-mic',
        'matching': 'bi-arrow-left-right'
    }
    
    return icons.get(question_type, 'bi-question-circle')

@register.simple_tag
def calculate_percentage(value, total):
    """
    Calculate a percentage value.
    Usage: {% calculate_percentage value total %}
    """
    if total == 0:
        return 0
    
    return (value / total) * 100