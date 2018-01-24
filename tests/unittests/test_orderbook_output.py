import asyncio
import json
import unittest

from pathlib import Path
from src.orderbook.orderbook import Orderbook


class TestOrderbookOutput(unittest.TestCase):
    resources = Path.cwd().joinpath('../resources')

    def setUp(self):
        self.pipe = asyncio.Queue()
        self.orderbook = Orderbook(None, None, None, 'BTC-USD', 10, 10)
        self.sample = {
            'sequence': 111,
            "bids":
                [["12345.56", "50.35", "order_id_1"],
                 ["12345.56", "100", "order_id_2"],
                 ["14038.13", "0.0003", "order_id_3"]]
            ,
            "asks":
                [["15000.00", "30.24", "order_id_4"],
                 ["15000.00", "199.22", "order_id_5"],
                 ["16000.00", "2.5", "order_id_6"]]

        }
        self.loop = asyncio.get_event_loop()

    def test_output_from_sample_snapshot(self):
        expected_output = {
            'product_id': 'BTC-USD',
            'sequence': 111,
            'bids': [
                ['14038.13', '0.0003', 'order_id_3'],
                ['12345.56', '50.35', 'order_id_1'],
                ['12345.56', '100', 'order_id_2']
            ],
            'asks': [
                ['15000.00', '30.24', 'order_id_4'],
                ['15000.00', '199.22', 'order_id_5'],
                ['16000.00', '2.5', 'order_id_6']
            ]}
        self.orderbook.orderbook_from_snapshot(self.sample)
        self.assertEqual(expected_output, self.orderbook.output_formatter())

    def test_there_should_be_no_output(self):
        no_data = {'product_id': 'BTC-USD', 'sequence': 111, 'bids': [], 'asks': []}
        self.orderbook.orderbook_from_snapshot(no_data)
        self.assertEqual(no_data, self.orderbook.output_formatter())

    def test_output_should_equal_sample_snapshot(self):
        with open(TestOrderbookOutput.resources.joinpath('sample_snapshot.txt'), 'r') as snapshot_file, \
                open(TestOrderbookOutput.resources.joinpath('output_sample_snapshot.txt'), 'r') as expected_file:
            snapshot = json.loads(snapshot_file.read())
            expected_output = json.loads(expected_file.read())
            self.orderbook.orderbook_from_snapshot(snapshot)
            self.assertEqual(expected_output, self.orderbook.output_formatter())

    def test_output_should_be_an_empty_book(self):
        self.orderbook.output_levels = 0
        event = {'price': '123', 'side': 'buy'}
        self.assertTrue(self.orderbook.should_output(event))

        event = {'price': '123', 'side': 'sell'}
        self.assertTrue(self.orderbook.should_output(event))

    def test_output_conditionals(self):
        with open(TestOrderbookOutput.resources.joinpath('sample_snapshot.txt'), 'r') as snapshot_file:
            snapshot = json.loads(snapshot_file.read())
        self.orderbook.orderbook_from_snapshot(snapshot)

        self.orderbook.num_output_lvls = 1
        event = {'price': '14038.01', 'side': 'sell'}
        self.assertTrue(self.orderbook.should_output(event))

        event = {'price': '14038.05', 'side': 'sell'}
        self.assertFalse(self.orderbook.should_output(event))

        event = {'price': '14038.01', 'side': 'buy'}
        self.assertTrue(self.orderbook.should_output(event))

        event = {'price': '14037.99', 'side': 'buy'}
        self.assertFalse(self.orderbook.should_output(event))
