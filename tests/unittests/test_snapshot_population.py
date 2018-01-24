import json
import unittest

from pathlib import Path
from sortedcontainers import SortedDict
from src.exceptions import SnapshotException
from src.orderbook.orderbook import Orderbook


class TestSnapshot(unittest.TestCase):
    resources_folder = Path.cwd().joinpath('../resources')

    def setUp(self):
        self.orderbook = self.orderbook = Orderbook(None, None, None, 'BTC-USD', 10, 10)

    def test_snaphsot_exception_should_be_thrown_no_seq_num(self):
        with self.assertRaises(SnapshotException) as cm:
            self.orderbook.orderbook_from_snapshot({})
        self.assertEqual(SnapshotException, type(cm.exception))

    def test_populate_empty_snapshot(self):
        with self.assertLogs(level='WARNING') as cm:
            expected_orderbook = {'bids': SortedDict(), 'asks': SortedDict()}
            self.orderbook.orderbook_from_snapshot({"sequence": 4865333025})
            self.assertEqual(expected_orderbook, self.orderbook.order_sides)
        self.assertEqual(cm.output, ['WARNING:root:4865333025 has no bids orders',
                                     'WARNING:root:4865333025 has no asks orders'])

    def test_logging_empty_orders(self):
        with self.assertLogs(level='WARNING') as cm:
            sample_snapshot = {"sequence": 4865333025, "bids": [[]], "asks": [[]]}
            self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(cm.output, ['WARNING:root:4865333025, bids, order 0 is empty',
                                     'WARNING:root:4865333025, asks, order 0 is empty'])

    def test_populate_snapshot_with_no_asks(self):
        sample_snapshot = {"sequence": 4865333025,
                           "bids": [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]],
                           "asks": []}
        expected_bids_result = SortedDict({
            14038.0: [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]]})
        self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(4865333025, self.orderbook.book_snapshot_seq_num)
        self.assertEqual(expected_bids_result, self.orderbook.order_sides.get('bids'))

    def test_populate_snapshot_with_no_bids(self):
        sample_snapshot = {"sequence": 4865333025,
                           "bids": [],
                           "asks": [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]]}
        expected_bids_result = SortedDict({14038.0: [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]]})
        self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(4865333025, self.orderbook.book_snapshot_seq_num)
        self.assertEqual(expected_bids_result, self.orderbook.order_sides.get('asks'))

    def test_populate_ordered_orders_with_empty_asks(self):
        sample_snapshot = {"sequence": 4865333025,
                           "bids": [
                               ["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"],
                               ["100.50", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]
                           ],
                           "asks": []}
        expected_bids_result = SortedDict({
            100.50: [["100.50", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]],
            14038.0: [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]]
        })
        self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(4865333025, self.orderbook.book_snapshot_seq_num)
        self.assertEqual(expected_bids_result, self.orderbook.order_sides.get('bids'))

    def test_populate_ordered_orders_empty_bids(self):
        sample_snapshot = {"sequence": 4865333025,
                           "bids": [],
                           "asks": [
                               ["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"],
                               ["100.50", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]
                           ]}
        expected_asks_result = SortedDict({
            100.50: [["100.50", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]],
            14038.0: [["14038", "0.52427801", "73fe8685-c1c4-4a23-804f-f5e5e431814a"]]
        })
        self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(4865333025, self.orderbook.book_snapshot_seq_num)
        self.assertEqual(expected_asks_result, self.orderbook.order_sides.get('asks'))

    def test_populate_ordered_orders(self):
        sample_snapshot = {"sequence": 1015,
                           "bids": [
                               ["115.50", "0.11", "order_id_1"],
                               ["115.50", "0.55", "order_id_2"],
                               ["1.00", "10.0", "order_id_3"]
                           ],
                           "asks": [
                               ["5.00", "20.0", "order_id_4"],
                               ["1000.24", "100.00", "order_id_5"],
                               ["1000.24", "110.00", "order_id_6"]
                           ]}
        expected_orderbook_result = {
            "bids": SortedDict({
                1.00: [["1.00", "10.0", "order_id_3"]],
                115.50: [["115.50", "0.11", "order_id_1"], ["115.50", "0.55", "order_id_2"]]
            }),
            "asks": SortedDict({
                5.00: [["5.00", "20.0", "order_id_4"]],
                1000.24: [["1000.24", "100.00", "order_id_5"], ["1000.24", "110.00", "order_id_6"]]
            })
        }
        self.orderbook.orderbook_from_snapshot(sample_snapshot)
        self.assertEqual(expected_orderbook_result, self.orderbook.order_sides)

    def test_with_sample_snapshot(self):
        with open(TestSnapshot.resources_folder.joinpath('sample_snapshot.txt'), 'r') as snapshot_file:
            snapshot = json.loads(snapshot_file.read())

            snapshot_bids = snapshot.get('bids')
            snapshot_bid_orders = []
            for bids in snapshot_bids:
                snapshot_bid_orders.append(float(bids[0]))
            snapshot_bid_sides = set(snapshot_bid_orders)

            snapshot_asks = snapshot.get('asks')
            snapshot_ask_orders = []
            for asks in snapshot_asks:
                snapshot_ask_orders.append(float(asks[0]))
            snapshot_ask_sides = set(snapshot_ask_orders)

            orderbook_bid_sides = self.orderbook.order_sides.get('bids').keys()
            orderbook_asks_sides = self.orderbook.order_sides.get('asks').keys()

            self.orderbook.orderbook_from_snapshot(snapshot)
            self.assertEqual(len(snapshot_bid_sides), len(orderbook_bid_sides))
            self.assertEqual(len(snapshot_ask_sides), len(orderbook_asks_sides))
            self.assertEqual(snapshot_bid_sides, orderbook_bid_sides)
            self.assertEqual(snapshot_ask_sides, orderbook_asks_sides)

            orderbook_bid_orders = []
            for orders in reversed(self.orderbook.order_sides.get('bids').values()):
                orderbook_bid_orders.extend(orders)

            orderbook_ask_orders = []
            for orders in self.orderbook.order_sides.get('asks').values():
                orderbook_ask_orders.extend(orders)

            self.assertEqual(len(snapshot_bids), len(orderbook_bid_orders))
            self.assertEqual(len(snapshot_asks), len(orderbook_ask_orders))
            self.assertEqual(snapshot_bids, orderbook_bid_orders)
            self.assertEqual(snapshot_asks, orderbook_ask_orders)
