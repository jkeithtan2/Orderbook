from collections import namedtuple
from decimal import Decimal

from src.orderbook.metadata import OrderIndexes


def unpack_snapshot(snapshot):
    SnapshotUnpacked = namedtuple('Snapshot', 'bids bid_levels cmp_bids asks ask_levels cmp_asks')
    bids = snapshot.get('bids')
    bid_orders = []
    cmp_bids = []
    for bid in bids:
        bid_orders.append(float(bid[0]))
        cmp_bids.append([Decimal(bid[OrderIndexes.PRICE]),
                         Decimal(bid[OrderIndexes.SIZE]), bid[OrderIndexes.ORDER_ID]])
    bid_levels = set(bid_orders)

    asks = snapshot.get('asks')
    ask_orders = []
    cmp_asks = []
    for ask in asks:
        cmp_asks.append([Decimal(ask[OrderIndexes.PRICE]),
                         Decimal(ask[OrderIndexes.SIZE]), ask[OrderIndexes.ORDER_ID]])
        ask_orders.append(float(ask[0]))
    ask_levels = set(ask_orders)
    return SnapshotUnpacked(bids, bid_levels, cmp_bids, asks, ask_levels, cmp_asks)


def get_all_orders_from_book(orderbook):
    FullFeedFormat = namedtuple('FullFeedFormat', 'bid_orders cmp_bids ask_orders cmp_asks')

    cmp_bids = []
    orderbook_bid_orders = []
    for orders in reversed(orderbook.order_sides.get('bids').values()):
        for order in orders:
            cmp_bids.append([Decimal(order[OrderIndexes.PRICE]),
                             Decimal(order[OrderIndexes.SIZE]), order[OrderIndexes.ORDER_ID]])
        orderbook_bid_orders.extend(orders)

    orderbook_ask_orders = []
    cmp_asks = []
    for orders in orderbook.order_sides.get('asks').values():
        for order in orders:
            cmp_asks.append([Decimal(order[OrderIndexes.PRICE]),
                             Decimal(order[OrderIndexes.SIZE]), order[OrderIndexes.ORDER_ID]])
        orderbook_ask_orders.extend(orders)
    return FullFeedFormat(orderbook_bid_orders, cmp_bids, orderbook_ask_orders, cmp_asks)
