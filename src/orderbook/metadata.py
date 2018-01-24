from enum import auto


class OrderIndexes:
    PRICE = 0
    SIZE = 1
    ORDER_ID = 2


class OrderSides:
    BID = 'bids'
    ASK = 'asks'


class ErrorLvls:
    WARN = auto()
    ERROR = auto()