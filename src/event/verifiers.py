from src.event.metadata import EventKeys, EventOrderTypes, EventSides
from src.exceptions import EventException


def should_process_event(event):
    event_type = event.get(EventKeys.TYPE)
    if event_type is None or event_type == EventOrderTypes.RECEIVED or (
            event_type == EventOrderTypes.DONE and event.get(EventKeys.PRICE) is None):
        return False
    format_errors = get_event_format_errors(event)
    if format_errors:
        raise EventException("{} for {}".format(format_errors, event), event)
    return True


def get_event_format_errors(event):
    errors = []
    side = event.get(EventKeys.SIDE)
    if side is None or side not in EventSides.ORDER_SIDES:
        errors.append(Errors.SIDE_ERROR)
    try:
        price = float(event.get(EventKeys.PRICE))
        if price < 0:
            errors.append(Errors.NEGATIVE_PRICE)
    except (TypeError, ValueError):
        errors.append(Errors.PRICE_NOT_NUMERIC)
    try:
        size = event.get(EventKeys.REMAINING_SIZE) or event.get(EventKeys.SIZE)
        if float(size) < 0:
            errors.append(Errors.NEGATIVE_SIZE)
    except (TypeError, ValueError):
        errors.append(Errors.SIZE_NOT_NUMERIC)
    if event.get(EventKeys.TYPE) == EventOrderTypes.DONE:
        try:
            event.get(EventKeys.REASON)
        except KeyError:
            errors.append(Errors.NO_REASON)
    return errors


class Errors:
    SIDE_ERROR = "event has side which is not buy/sell"
    NO_REASON = "Done event has no reason"
    SIZE_NOT_NUMERIC = "Size is not numeric type"
    NEGATIVE_SIZE = "Size is negative"
    PRICE_NOT_NUMERIC = "Price is not numeric type"
    NEGATIVE_PRICE = "Price is negative"
