def cast_to_string(value):
    try:
        return str(value)
    except (ValueError, TypeError):
        return None

def cast_to_boolean(value):
    try:
        return bool(value)
    except (ValueError, TypeError):
        return None

def cast_to_integer(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
    
def cast_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None