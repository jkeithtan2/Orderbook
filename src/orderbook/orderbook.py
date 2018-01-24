import asyncio
import logging

from tenacity import RetryError

from src import app_config
from decimal import Decimal
from sortedcontainers import SortedDict
from src.event.verifiers import should_process_event
from src.event.metadata import EventKeys, EventOrderTypes, EventDoneReasons, EventSides
from src.exceptions import EventException, SnapshotException, SnapshotHttpException
from src.io.io_interfaces import Pipeline
from src.orderbook.metadata import OrderSides, OrderIndexes, ErrorLvls


class Orderbook:
    def __init__(self, event_reader, l2_writer, http_client, product_id, num_output_levels, error_threshold):
        self.event_reader = event_reader
        self.l2_writer = l2_writer
        self.http_client = http_client
        self.product_id = product_id or ''
        self.num_output_lvls = num_output_levels or 25
        self.error_threshold = error_threshold or 10
        self.book_snapshot_seq_num = -1
        self.last_output_seq_num = -1
        self.curr_seq_num = 0
        self.error_count = 0
        self.takers_match_prices = {
            OrderSides.BID: {},
            OrderSides.ASK: {}
        }
        self.order_sides = {
            OrderSides.BID: SortedDict({}),
            OrderSides.ASK: SortedDict({})
        }
        self.bid_values = self.order_sides.get(OrderSides.BID).values()
        self.ask_values = self.order_sides.get(OrderSides.ASK).values()
        self.bid_levels = self.order_sides.get(OrderSides.BID).keys()
        self.ask_levels = self.order_sides.get(OrderSides.ASK).keys()

    async def begin_consume(self):
        start_trigger = await self.event_reader.pipe.get()
        if start_trigger == Pipeline.states.STARTED:
            try:
                await self.build_orderbook()
            except RetryError:
                self.event_reader.state = Pipeline.states.STOP_SENDING
                raise SnapshotHttpException('Unable to get snapshot for product {} closing feed'
                                            .format(self.product_id))
        await self.consume()

    async def consume(self):
        while True:
            try:
                event = await self.event_reader.pipe.get()
                if event == Pipeline.states.CLOSING_PIPE:
                    break
                if self.process_event(event) and self.should_output(event) \
                        and self.last_output_seq_num < self.curr_seq_num:
                    self.last_output_seq_num = self.curr_seq_num
                    output = self.output_formatter()
                    await self.l2_writer.pipe.put(output)
                    asyncio.sleep(0)
            except (AttributeError, EventException, KeyError) as e:
                self.handle_error(e, ErrorLvls.ERROR)
            if self.error_count > self.error_threshold:
                try:
                    await self.build_orderbook()
                # on http error tell reset error count to give http time to recover, continue processing events
                except RetryError:
                    logging.error('Unable to get snapshot for product {}'.format(self.product_id))
                finally:
                    self.error_count = 0

    def process_event(self, event):
        if self.is_valid_seq_num(event) and should_process_event(event):
            event_type = event.get(EventKeys.TYPE)
            price = event.get(EventKeys.PRICE)
            price_key = float(price)
            order_id = event.get(EventKeys.ORDER_ID) or event.get(EventKeys.MAKER_ID)
            event_size = event.get(EventKeys.REMAINING_SIZE) or event.get(EventKeys.SIZE)
            order_side = get_book_side(event.get(EventKeys.SIDE))
            orderbook_side = self.order_sides.get(order_side)
            orders = orderbook_side.get(price_key)
            if event_type == EventOrderTypes.OPEN:
                orderbook_side.setdefault(price_key, []).append([price, event_size, order_id])
            elif event_type == EventOrderTypes.MATCH:
                try:
                    order = next(order for order in orders if order[OrderIndexes.ORDER_ID] == order_id)
                    new_size = Decimal(order[OrderIndexes.SIZE]) - Decimal(event_size)
                    if new_size < 0:
                        self.handle_error("match size larger than book size for {}".format(event), ErrorLvls.WARN)
                    order[OrderIndexes.SIZE] = str(max(new_size, 0))
                except (ValueError, TypeError, StopIteration, KeyError):
                    raise EventException("match not on book for event {}".format(event), event)
            elif event_type == EventOrderTypes.DONE and (
                    event[EventKeys.REASON] == EventDoneReasons.CANCEL or (
                    event[EventKeys.REASON] == EventDoneReasons.FILLED and orders is not None)):
                try:
                    order_index = next(i for i, order in enumerate(orders) if order[OrderIndexes.ORDER_ID] == order_id)
                    orders.pop(order_index)
                    if not orders:
                        del orderbook_side[price_key]
                except (ValueError, TypeError, StopIteration, KeyError):
                    raise EventException("filled/canceled should be on book for {}".format(event), event)
            else:
                return False
            return True

    def is_valid_seq_num(self, event):
        try:
            event_seq_num = event.get(EventKeys.SEQ)
            if event_seq_num <= self.curr_seq_num:
                return False
            if self.curr_seq_num + 1 < event_seq_num:
                self.handle_error("jump in sequence number between book-{} and event-{}"
                                  .format(self.curr_seq_num, event_seq_num), ErrorLvls.WARN)
            if event_seq_num > self.curr_seq_num:
                self.curr_seq_num = event_seq_num
            return True
        except TypeError:
            raise EventException("seq number key is missing", event)

    async def build_orderbook(self):
        init_snapshot = await self.http_client.get_orderbook_snapshot(self.product_id,
                                                                      app_config.http.get('timeout'))
        self.orderbook_from_snapshot(init_snapshot)

    def orderbook_from_snapshot(self, book_snapshot):
        snapshot_seq_num = book_snapshot.get(EventKeys.SEQ)
        if snapshot_seq_num is None or snapshot_seq_num <= self.book_snapshot_seq_num:
            raise SnapshotException("snapshot seq num {} is before order books".format(snapshot_seq_num))
        [values.clear() for values in self.order_sides.values()]
        for side in [OrderSides.BID, OrderSides.ASK]:
            orderbook_side = self.order_sides.get(side)
            if book_snapshot.get(side) is not None:
                for index, order in enumerate(book_snapshot.get(side)):
                    if order and len(order) == 3:
                        price = float(order[OrderIndexes.PRICE])
                        orderbook_side.setdefault(price, []).append(order)
                    else:
                        logging.warning("{}, {}, order {} is empty".format(snapshot_seq_num, side, index))
            else:
                logging.warning("{} has no {} orders".format(snapshot_seq_num, side))
        self.curr_seq_num = snapshot_seq_num
        self.book_snapshot_seq_num = snapshot_seq_num

    def should_output(self, event):
        try:
            price = float(event.get(EventKeys.PRICE))
            if event.get(EventKeys.SIDE) == EventSides.SELL:
                return (len(self.ask_levels) < self.num_output_lvls + 1
                        or price < self.ask_levels[self.num_output_lvls])
            elif event.get(EventKeys.SIDE) == EventSides.BUY:
                num_bid_lvls = len(self.bid_levels)
                return (num_bid_lvls < self.num_output_lvls + 1 or
                        price > self.bid_levels[num_bid_lvls - self.num_output_lvls - 1])
        except IndexError as e:
            logging.error("Should output index out of bounds error for event {}".format(e))
            return False

    def output_formatter(self):
        output_bids, output_asks = [], []
        bid_values_len = len(self.bid_values)
        ask_values_len = len(self.ask_values)
        for i in range(self.num_output_lvls):
            if i < bid_values_len:
                output_bids.extend(self.bid_values[bid_values_len - i - 1])
            if i < ask_values_len:
                output_asks.extend(self.ask_values[i])
        return {
            "product_id": self.product_id,
            "sequence": self.curr_seq_num,
            "bids": output_bids,
            "asks": output_asks
        }

    def handle_error(self, msg, logginglevel):
        if logginglevel == ErrorLvls.WARN:
            logging.warning(msg)
        else:
            logging.error(msg)
        self.error_count += 1


def get_book_side(event_side):
    if EventSides.BUY == event_side:
        return OrderSides.BID
    elif EventSides.SELL == event_side:
        return OrderSides.ASK
    return None

