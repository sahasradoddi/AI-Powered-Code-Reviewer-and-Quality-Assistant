# These imports are unused on purpose
import math
import json
from datetime import datetime

def add_numbers(a, b):
    """Simple function that doesn't use the imported modules."""
    result = a + b
    # Only use built-ins, no use of math/json/datetime
    if result > 10:
        result -= 1
    return result
