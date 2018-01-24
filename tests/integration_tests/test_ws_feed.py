import unittest
import aiohttp
import asyncio

from src import app_config
from src.io import io_interfaces
from src.event.metadata import EventKeys
from src.exceptions import SocketException


class TestWSFeed(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()

    def test_full_should_succeed(self):
        async def test_runner():
            async with aiohttp.ClientSession() as session:
                dispatcher_mock = EventDispatcherMock()
                task = asyncio.ensure_future(
                    io_interfaces.get_full_feed(session, dispatcher_mock, app_config.full_feed_subscribe_msg))
                await asyncio.sleep(5)
                task.cancel()
                self.assertEqual(set(app_config.subscribed_product_ids), set(dispatcher_mock.triggered_product_list))

        self.loop.run_until_complete(test_runner())

    def test_ws_error_handling(self):
        async def test_runner():
            async with aiohttp.ClientSession() as session:
                with self.assertRaises(SocketException):
                    await io_interfaces.get_full_feed(session,
                                                      EventDispatcherMock(),
                                                      {"type": "subscribe", "channels": [{"name": "full",
                                                                                          "product_ids": []}]})
                    await asyncio.sleep(5)

        self.loop.run_until_complete(test_runner())


class EventDispatcherMock:
    def __init__(self):
        self.triggered_product_list = []

    async def dispatch(self, event):
        self.triggered_product_list.append(event.get(EventKeys.PRODUCT_ID))
