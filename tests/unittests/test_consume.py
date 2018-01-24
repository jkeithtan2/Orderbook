import asyncio
import json
import unittest
from pathlib import Path

from tenacity import RetryError, retry_if_exception_type, stop_after_attempt, retry

from src.exceptions import SnapshotHttpException
from src.io.io_interfaces import Pipeline
from src.orderbook.metadata import OrderSides
from src.orderbook.orderbook import Orderbook
from tests.unittests import test_utils


class TestConsume(unittest.TestCase):
    resources = Path.cwd().joinpath('../resources')

    def setUp(self):
        self.reader = Pipeline(asyncio.Queue())
        self.writer = Pipeline(asyncio.Queue())
        self.reader.pipe.state = Pipeline.states.STARTED
        self.orderbook = Orderbook(self.reader, self.writer, None, 'BTC-EUR', 10, 10)
        self.loop = asyncio.get_event_loop()
        self.event_feed = []
        with open(TestConsume.resources.joinpath('sample_snapshot.txt'), 'r') as snapshot_file:
            self.default_snapshot = json.loads(snapshot_file.read())

    async def setUp_run_consume(self):
        for line in self.event_feed:
            await self.reader.pipe.put(json.loads(line))
        await self.reader.pipe.put(Pipeline.states.CLOSING_PIPE)
        await self.orderbook.consume()

    async def setUp_begin_consume(self):
        await self.reader.pipe.put(Pipeline.states.STARTED)
        await self.reader.pipe.put(Pipeline.states.CLOSING_PIPE)
        await self.orderbook.begin_consume()

    def test_async_runners(self):
        self.orderbook.orderbook_from_snapshot(self.default_snapshot)

        async def test_runner():
            await self.setUp_run_consume()

        self.loop.run_until_complete(test_runner())

    def test_error_dataset(self):
        with open(TestConsume.resources.joinpath('error_dataset_1/empty_snapshot.txt'), 'r') as snapshot_file, \
                open(TestConsume.resources.joinpath('error_dataset_1/error_dataset_1_feed.txt'), 'r') as feed_file, \
                open(TestConsume.resources.joinpath('error_dataset_1/expected_results.txt'), 'r') as result_file:
            snapshot = json.loads(snapshot_file.read())
            self.event_feed = feed_file.readlines()
            lines = result_file.readlines()
        self.orderbook.orderbook_from_snapshot(snapshot)
        self.expected_results = [json.loads(result) for result in lines]

        async def test_runner():
            actual_results = []
            with self.assertLogs(level='WARNING') as cm:
                await self.setUp_run_consume()
                while not self.writer.pipe.empty():
                    actual_results.append(await self.writer.pipe.get())
            self.assertEqual(self.expected_results, actual_results)
            self.assertEqual(3, self.orderbook.error_count)
            self.assertTrue(cm.output[0].startswith('ERROR:root:filled/canceled should be on book for'))
            self.assertEqual('WARNING:root:jump in sequence number between book-4864284471 and event-4864284473',
                             cm.output[1])
            self.assertEqual('WARNING:root:jump in sequence number between book-4864284473 and event-4864284475',
                             cm.output[2])

        self.loop.run_until_complete(test_runner())

    def test_simulate_book_rebuild_after_errors(self):
        with open(TestConsume.resources.joinpath('rebuild_dataset/rebuild_feed.txt'), 'r') as feed_file:
            self.event_feed = feed_file.readlines()
            self.orderbook.http_client = DefaultHttpClientMock(self.default_snapshot)
        self.orderbook.error_threshold = 2

        async def test_runner():
            with self.assertLogs(level='WARNING'):
                await self.setUp_run_consume()
                unpacked_snapshot = test_utils.unpack_snapshot(self.default_snapshot)
                orderbook_bid_sides = self.orderbook.order_sides.get(OrderSides.BID).keys()
                self.assertEqual(2, self.orderbook.error_count)
                self.assertEqual(unpacked_snapshot.bid_levels, orderbook_bid_sides)

        self.loop.run_until_complete(test_runner())

    def test_simulate_btc_eur_older_than_snapshot_data(self):
        with open(TestConsume.resources.joinpath('btc_eur/1st_snapshot.txt'), 'r') as snapshot_file:
            snapshot = json.loads(snapshot_file.read())
        self.orderbook.orderbook_from_snapshot(snapshot)
        with open(TestConsume.resources.joinpath('btc_eur/before_1st_snapshot_feed.txt'), 'r') as feed_file:
            self.event_feed = feed_file.readlines()

        async def test_runner():
            await self.setUp_run_consume()
            unpacked_snapshot = test_utils.unpack_snapshot(snapshot)
            orderbook_fullfeed = test_utils.get_all_orders_from_book(self.orderbook)
            self.assertEqual(unpacked_snapshot.bids, orderbook_fullfeed.bid_orders)
            self.assertEqual(unpacked_snapshot.asks, orderbook_fullfeed.ask_orders)
            await self.reader.pipe.put(Pipeline.states.CLOSING_PIPE)

        self.loop.run_until_complete(test_runner())

    def test_simulate_btc_eur(self):
        with open(TestConsume.resources.joinpath('btc_eur/1st_snapshot.txt'), 'r') as first_snapshot_file, \
                open(TestConsume.resources.joinpath('btc_eur/2nd_snapshot.txt'), 'r') as second_snapshot_file, \
                open(TestConsume.resources.joinpath('btc_eur/before_2nd_snapshot_feed.txt'), 'r') as feed_file:
            first_snapshot = json.loads(first_snapshot_file.read())
            second_snapshot = json.loads(second_snapshot_file.read())
            self.event_feed = feed_file.readlines()
        self.orderbook.orderbook_from_snapshot(first_snapshot)
        self.orderbook.error_threshold = 10

        async def test_runner():
            await self.setUp_run_consume()
            unpacked_second_snapshot = test_utils.unpack_snapshot(second_snapshot)
            book_orders = test_utils.get_all_orders_from_book(self.orderbook)

            self.assertEqual(unpacked_second_snapshot.ask_levels, self.orderbook.order_sides.get(OrderSides.ASK).keys())
            self.assertEqual(unpacked_second_snapshot.bid_levels, self.orderbook.order_sides.get(OrderSides.BID).keys())
            self.assertEqual(len(unpacked_second_snapshot.bids), len(unpacked_second_snapshot.cmp_bids))
            self.assertEqual(len(unpacked_second_snapshot.asks), len(unpacked_second_snapshot.cmp_asks))
            self.assertEqual(len(book_orders.ask_orders), len(book_orders.cmp_asks))
            self.assertEqual(len(unpacked_second_snapshot.bids), len(book_orders.bid_orders))
            self.assertEqual(len(unpacked_second_snapshot.asks), len(book_orders.ask_orders))
            self.assertEqual(unpacked_second_snapshot.cmp_asks, book_orders.cmp_asks)
            self.assertEqual(unpacked_second_snapshot.cmp_bids, book_orders.cmp_bids)
        self.loop.run_until_complete(test_runner())

    def test_simulate_ltc_usd(self):
        with open(TestConsume.resources.joinpath('ltc_usd/1st_snapshot.txt'), 'r') as first_snapshot_file, \
                open(TestConsume.resources.joinpath('ltc_usd/2nd_snapshot.txt'), 'r') as second_snapshot_file, \
                open(TestConsume.resources.joinpath('ltc_usd/before_2nd_snapshot_feed.txt'), 'r') as feed_file:
            first_snapshot = json.loads(first_snapshot_file.read())
            second_snapshot = json.loads(second_snapshot_file.read())
            self.event_feed = feed_file.readlines()
        self.orderbook.orderbook_from_snapshot(first_snapshot)
        self.orderbook.error_threshold = 10

        async def test_runner():
            await self.setUp_run_consume()
            unpacked_second_snapshot = test_utils.unpack_snapshot(second_snapshot)
            book_orders = test_utils.get_all_orders_from_book(self.orderbook)
            self.assertEqual(len(unpacked_second_snapshot.ask_levels),
                             len(self.orderbook.order_sides.get(OrderSides.ASK).keys()))
            self.assertEqual(unpacked_second_snapshot.ask_levels, self.orderbook.order_sides.get(OrderSides.ASK).keys())
            self.assertEqual(unpacked_second_snapshot.bid_levels, self.orderbook.order_sides.get(OrderSides.BID).keys())

            self.assertEqual(len(unpacked_second_snapshot.bids), len(unpacked_second_snapshot.cmp_bids))
            self.assertEqual(len(unpacked_second_snapshot.asks), len(unpacked_second_snapshot.cmp_asks))
            self.assertEqual(len(book_orders.ask_orders), len(book_orders.cmp_asks))
            self.assertEqual(len(unpacked_second_snapshot.bids), len(book_orders.bid_orders))
            self.assertEqual(len(unpacked_second_snapshot.asks), len(book_orders.ask_orders))
            self.assertEqual(unpacked_second_snapshot.cmp_asks, book_orders.cmp_asks)
            self.assertEqual(unpacked_second_snapshot.cmp_bids, book_orders.cmp_bids)
        self.loop.run_until_complete(test_runner())

    def test_begin_consume_happy_flow(self):
        self.orderbook.http_client = DefaultHttpClientMock(self.default_snapshot)

        async def test_runner():
            await self.setUp_begin_consume()
            unpacked_snapshot = test_utils.unpack_snapshot(self.default_snapshot)
            self.assertEqual(unpacked_snapshot.bid_levels, self.orderbook.order_sides.get(OrderSides.BID).keys())
            self.assertEqual(unpacked_snapshot.ask_levels, self.orderbook.order_sides.get(OrderSides.ASK).keys())

        self.loop.run_until_complete(test_runner())

    def test_begin_consume_stop_sending(self):
        self.orderbook.http_client = FaultyHttpMock()

        async def test_runner():
            with self.assertRaises(SnapshotHttpException):
                await self.setUp_begin_consume()
        self.loop.run_until_complete(test_runner())


class DefaultHttpClientMock:
    def __init__(self, resp):
        self.resp = resp

    async def get_orderbook_snapshot(self, product_id, http_timeout):
        await asyncio.sleep(0)
        return self.resp


class FaultyHttpMock:
    @retry(retry=retry_if_exception_type(SnapshotHttpException),
           stop=stop_after_attempt(1))
    async def get_orderbook_snapshot(self, product_id, http_timeout):
        raise SnapshotHttpException
