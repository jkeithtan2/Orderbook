import unittest

from sortedcontainers import SortedDict
from src.event.metadata import EventKeys, EventSides
from src.exceptions import EventException
from src.orderbook.metadata import OrderSides
from src.orderbook.orderbook import Orderbook


class TestEventHandling(unittest.TestCase):
    open_buy_1 = {"type": "open",
                  "side": "buy",
                  "price": "123.45",
                  "order_id": "order_id_1",
                  "remaining_size": "100",
                  "product_id": "BTC-USD",
                  "sequence": 1,
                  "time": "2018-01-18T00:00:00.000000Z"}

    done_market = {"type": "done",
                   "side": "buy",
                   "order_id": "order_id_6",
                   "reason": "filled",
                   "product_id": "BTC-USD",
                   "remaining_size": "0.00000000",
                   "sequence": 1,
                   "time": "2018-01-15T11:53:14.529000Z"}

    match_buy_1 = {"type": "match",
                   "trade_id": 111,
                   "maker_order_id": open_buy_1.get('order_id'),
                   "taker_order_id": 'order_id_7',
                   "side": "buy",
                   "size": "50.7",
                   "price": "123.45",
                   "product_id": "BTC-USD",
                   "sequence": 1,
                   "time": "2018-01-18T01:00:00.000000Z"}

    open_buy_2 = dict(open_buy_1)
    open_buy_2[EventKeys.PRICE] = "10.10"
    open_buy_2[EventKeys.ORDER_ID] = "order_id_2"

    open_buy_3 = dict(open_buy_1)
    open_buy_3[EventKeys.PRICE] = "123.45"
    open_buy_3[EventKeys.ORDER_ID] = "order_id_3"

    open_sell_1 = dict(open_buy_1)
    open_sell_1[EventKeys.SIDE] = EventSides.SELL
    open_sell_1[EventKeys.PRICE] = "555"
    open_sell_1[EventKeys.REMAINING_SIZE] = "1000"
    open_sell_1[EventKeys.ORDER_ID] = "order_id_4"

    open_sell_2 = dict(open_sell_1)
    open_sell_2[EventKeys.REMAINING_SIZE] = "2000"
    open_sell_2[EventKeys.ORDER_ID] = "order_id_5"

    done_limit_1 = dict(done_market)
    done_limit_1[EventKeys.ORDER_ID] = open_buy_1.get(EventKeys.ORDER_ID)
    done_limit_1[EventKeys.PRICE] = open_buy_1.get(EventKeys.PRICE)

    done_limit_2 = dict(done_market)
    done_limit_2[EventKeys.ORDER_ID] = open_buy_2.get(EventKeys.ORDER_ID)
    done_limit_2[EventKeys.PRICE] = open_buy_2.get(EventKeys.PRICE)

    match_sell_1 = dict(match_buy_1)
    match_sell_1[EventKeys.MAKER_ID] = open_sell_1[EventKeys.ORDER_ID]
    match_sell_1[EventKeys.SIDE] = EventSides.SELL
    match_sell_1[EventKeys.PRICE] = open_sell_1[EventKeys.PRICE]
    match_sell_1[EventKeys.SIZE] = "489.1533451"

    def setUp(self):
        self.orderbook = self.orderbook = Orderbook(None, None, None, 'BTC-USD', 10, 10)
        self.orderbook.curr_seq_num = 0
        self.test_seq_num = 1

    def set_and_increment_seq(self, event):
        event[EventKeys.SEQ] = self.test_seq_num
        self.test_seq_num += 1

    def test_sequence_number_should_decrement_by_one(self):
        expected_result = self.orderbook.curr_seq_num
        TestEventHandling.open_buy_2[EventKeys.SEQ] = -1
        self.orderbook.process_event(TestEventHandling.open_buy_2)
        self.assertEqual(expected_result, self.orderbook.curr_seq_num)

    def test_sequence_number_should_increment_by_one(self):
        self.set_and_increment_seq(TestEventHandling.open_buy_2)
        self.orderbook.process_event(TestEventHandling.open_buy_2)
        self.assertEqual(TestEventHandling.open_buy_2.get(EventKeys.SEQ), self.orderbook.curr_seq_num)

    def test_sequence_number_should_increment_by_two(self):
        with self.assertLogs(level='WARNING') as cm:
            self.set_and_increment_seq(TestEventHandling.open_buy_2)
            self.set_and_increment_seq(TestEventHandling.open_buy_2)
            self.orderbook.process_event(TestEventHandling.open_buy_2)
        self.assertEqual(TestEventHandling.open_buy_2.get(EventKeys.SEQ), self.orderbook.curr_seq_num)
        self.assertEqual(cm.output, ['WARNING:root:jump in sequence number between book-0 and event-2'])

    def test_adding_open_orders_on_bid_side_of_book(self):
        expected_result_open_buy_2 = {
            float(TestEventHandling.open_buy_2[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_2)]
        }
        self.set_and_increment_seq(TestEventHandling.open_buy_2)
        self.orderbook.process_event(TestEventHandling.open_buy_2)
        self.assertEqual(expected_result_open_buy_2, self.orderbook.order_sides.get(OrderSides.BID))

        expected_result_open_buy_1 = {
            float(TestEventHandling.open_buy_1[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_1)],
            float(TestEventHandling.open_buy_2[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_2)]
        }
        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)
        self.assertEqual(expected_result_open_buy_1, self.orderbook.order_sides.get(OrderSides.BID))

        expected_result_same_price = {
            float(TestEventHandling.open_buy_1[EventKeys.PRICE]):
                [create_order(TestEventHandling.open_buy_1),
                 create_order(TestEventHandling.open_buy_3)],
            float(TestEventHandling.open_buy_2[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_2)]
        }
        self.set_and_increment_seq(TestEventHandling.open_buy_3)
        self.orderbook.process_event(TestEventHandling.open_buy_3)
        self.assertEqual(expected_result_same_price, self.orderbook.order_sides.get(OrderSides.BID))

    def test_adding_open_orders_on_both_sides_of_book(self):
        expected_result_open_buy_1 = {
            float(TestEventHandling.open_buy_1[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_1)]
        }
        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)
        self.assertEqual(expected_result_open_buy_1, self.orderbook.order_sides.get(OrderSides.BID))

        expected_result_open_sell_1 = {
            OrderSides.BID: {
                float(TestEventHandling.open_buy_1[EventKeys.PRICE]): [
                    create_order(TestEventHandling.open_buy_1)]
            },
            OrderSides.ASK: {
                float(TestEventHandling.open_sell_1[EventKeys.PRICE]): [
                    create_order(TestEventHandling.open_sell_1)]
            }
        }
        self.set_and_increment_seq(TestEventHandling.open_sell_1)
        self.orderbook.process_event(TestEventHandling.open_sell_1)
        self.assertEqual(expected_result_open_sell_1, self.orderbook.order_sides)

        expected_result_open_same_sell_1 = {
            OrderSides.BID: {
                float(TestEventHandling.open_buy_1[EventKeys.PRICE]): [
                    create_order(TestEventHandling.open_buy_1)]
            },
            OrderSides.ASK: {
                float(TestEventHandling.open_sell_1[EventKeys.PRICE]): [
                    create_order(TestEventHandling.open_sell_1),
                    create_order(TestEventHandling.open_sell_2)]
            }
        }
        self.set_and_increment_seq(TestEventHandling.open_sell_2)
        self.orderbook.process_event(TestEventHandling.open_sell_2)
        self.assertEqual(expected_result_open_same_sell_1, self.orderbook.order_sides)

    def test_done_events(self):
        self.set_and_increment_seq(TestEventHandling.open_sell_2)
        self.orderbook.process_event(TestEventHandling.done_market)
        self.assertEqual(self.orderbook.order_sides, {OrderSides.BID: SortedDict({}),
                                                      OrderSides.ASK: SortedDict({})})

    def test_done_limit_orders(self):
        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)

        self.set_and_increment_seq(TestEventHandling.done_limit_1)
        self.orderbook.process_event(TestEventHandling.done_limit_1)
        self.assertEqual({OrderSides.BID: SortedDict({}), OrderSides.ASK: SortedDict({})}, self.orderbook.order_sides)

        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)
        self.set_and_increment_seq(TestEventHandling.open_buy_2)
        self.orderbook.process_event(TestEventHandling.open_buy_2)

        done_limit_2 = dict(self.done_market)
        done_limit_2[EventKeys.ORDER_ID] = TestEventHandling.open_buy_2.get(EventKeys.ORDER_ID)
        done_limit_2[EventKeys.PRICE] = TestEventHandling.open_buy_2.get(EventKeys.PRICE)
        self.set_and_increment_seq(done_limit_2)
        self.orderbook.process_event(done_limit_2)

        expected_result_done_limit_2 = {
            float(TestEventHandling.open_buy_1[EventKeys.PRICE]): [create_order(TestEventHandling.open_buy_1)]
        }
        self.assertEqual(expected_result_done_limit_2, self.orderbook.order_sides.get(OrderSides.BID))

    def test_match_orders(self):
        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)
        self.set_and_increment_seq(TestEventHandling.match_buy_1)
        self.orderbook.process_event(TestEventHandling.match_buy_1)

        expected_bid_order = dict(TestEventHandling.open_buy_1)
        expected_bid_order[EventKeys.REMAINING_SIZE] = '49.3'

        expected_bid_book_after_match_buy_1 = {
            float(expected_bid_order[EventKeys.PRICE]): [create_order(expected_bid_order)]
        }
        self.assertEqual(expected_bid_book_after_match_buy_1, self.orderbook.order_sides.get(OrderSides.BID))

        self.set_and_increment_seq(TestEventHandling.open_sell_1)
        self.orderbook.process_event(TestEventHandling.open_sell_1)
        self.set_and_increment_seq(TestEventHandling.match_sell_1)
        self.orderbook.process_event(TestEventHandling.match_sell_1)

        expected_sell_order = dict(TestEventHandling.open_sell_1)
        expected_sell_order[EventKeys.REMAINING_SIZE] = '510.8466549'
        expected_bid_book_after_match_sell_1 = {
            float(expected_sell_order[EventKeys.PRICE]): [create_order(expected_sell_order)]
        }

        expected_result_match_buy_1_sell_1 = {
            OrderSides.BID: expected_bid_book_after_match_buy_1,
            OrderSides.ASK: expected_bid_book_after_match_sell_1
        }
        self.assertEqual(expected_result_match_buy_1_sell_1, self.orderbook.order_sides)

        with self.assertLogs(level='WARNING') as cm:
            self.set_and_increment_seq(TestEventHandling.open_buy_1)
            self.orderbook.process_event(TestEventHandling.open_buy_1)
            self.set_and_increment_seq(TestEventHandling.match_buy_1)
            self.orderbook.process_event(TestEventHandling.match_buy_1)

            expected_bid_order = dict(TestEventHandling.open_buy_1)
            expected_bid_order[EventKeys.REMAINING_SIZE] = '0'

            expected_bid_book_after_second_buy_second_match = {
                float(expected_bid_order[EventKeys.PRICE]):
                    [create_order(expected_bid_order), create_order(TestEventHandling.open_buy_1)]
            }
            expected_result_match_after_second_buy_second_match = {
                OrderSides.BID: expected_bid_book_after_second_buy_second_match,
                OrderSides.ASK: expected_bid_book_after_match_sell_1
            }
            self.assertEqual(expected_result_match_after_second_buy_second_match, self.orderbook.order_sides)
        self.assertTrue(cm.output[0].startswith('WARNING:root:match size larger than book size for'))

    def testing_all_order_types_together(self):
        with self.assertRaises(EventException) as cm:
            self.set_and_increment_seq(TestEventHandling.match_buy_1)
            self.orderbook.process_event(TestEventHandling.match_buy_1)
        self.assertEqual(EventException, type(cm.exception))

        self.set_and_increment_seq(TestEventHandling.open_buy_1)
        self.orderbook.process_event(TestEventHandling.open_buy_1)
        self.set_and_increment_seq(TestEventHandling.open_sell_1)
        self.orderbook.process_event(TestEventHandling.open_sell_1)

        self.set_and_increment_seq(TestEventHandling.done_limit_1)
        self.orderbook.process_event(TestEventHandling.done_limit_1)

        expected_result_open_sell_1 = {
            OrderSides.BID: {
            },
            OrderSides.ASK: {
                float(TestEventHandling.open_sell_1[EventKeys.PRICE]): [
                    create_order(TestEventHandling.open_sell_1)]
            }
        }
        self.assertEqual(expected_result_open_sell_1, self.orderbook.order_sides)
        self.orderbook.process_event(TestEventHandling.done_market)
        self.assertEqual(expected_result_open_sell_1, self.orderbook.order_sides)


def create_order(event):
    return [event[EventKeys.PRICE],
            event[EventKeys.REMAINING_SIZE],
            event[EventKeys.ORDER_ID]]
