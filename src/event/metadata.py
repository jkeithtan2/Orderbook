class EventKeys:
    SEQ = 'sequence'
    PRICE = 'price'
    REMAINING_SIZE = 'remaining_size'
    SIZE = 'size'
    REASON = 'reason'
    ORDER_ID = 'order_id'
    TYPE = 'type'
    SIDE = 'side'
    MAKER_ID = "maker_order_id"
    TAKE_ID = "taker_order_id"
    PRODUCT_ID = "product_id"


class EventOrderTypes:
    OPEN = 'open'
    MATCH = 'match'
    RECEIVED = 'received'
    DONE = 'done'


class EventSides:
    BUY = 'buy'
    SELL = 'sell'
    ORDER_SIDES = [BUY, SELL]


class EventDoneReasons:
    CANCEL = 'canceled'
    FILLED = 'filled'
