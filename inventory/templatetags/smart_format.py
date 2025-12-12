from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def smart_decimal(value):
    """
    Hiển thị số đẹp:
    100.0000 → 100
    0.5000   → 0.5
    1.7500   → 1.75
    """
    try:
        num = Decimal(str(value))
        if num % 1 == 0:
            return int(num)
        else:
            # Loại bỏ số 0 thừa
            return float(num)
    except:
        return value