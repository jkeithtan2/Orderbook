import unittest
import asyncio
import aiohttp
from tenacity import RetryError

from src.exceptions import SnapshotHttpException
from src.io.io_interfaces import SnapshotHttpClient


class TestHttpClient(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_http_client_should_return_success(self):
        async def test_runner():
            async with aiohttp.ClientSession() as session:
                http_client = SnapshotHttpClient(session)
                resp = await http_client.get_orderbook_snapshot('LTC-USD', 180)
            self.assertIsNotNone(resp)

        self.loop.run_until_complete(test_runner())

    def test_http_client_should_fail(self):
        async def test_runner():
            async with aiohttp.ClientSession() as session:
                http_client = SnapshotHttpClient(session)
                with self.assertRaises(RetryError):
                    await http_client.get_orderbook_snapshot('ABCDEF', 180)
        self.loop.run_until_complete(test_runner())