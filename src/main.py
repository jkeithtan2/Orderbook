import logging
import os
import aiohttp
import asyncio

from src import app_config
from src.io.dispatchers import EventDispatcher
from src.exceptions import InitException
from src.io.io_interfaces import SnapshotHttpClient, get_full_feed, Pipeline, write_to_stdout
from src.orderbook.orderbook import Orderbook


async def start_event_reader(event_feed):
    await event_feed


async def start_orderbook_consume(orderbook):
    await orderbook.begin_consume()


async def start_l2_writer(output_writer):
    await output_writer


async def start_app(app_loop):
    for sub_prod in app_config.subscribed_product_ids:
        if sub_prod not in app_config.product_list:
            raise InitException()

    tasks = []
    product_event_readers = {}
    l2_writer_pipeline = Pipeline(asyncio.Queue())
    l2_writer = write_to_stdout(l2_writer_pipeline)
    l2_writer_task = asyncio.ensure_future(start_l2_writer(l2_writer))
    tasks.append(l2_writer_task)
    async with aiohttp.ClientSession(loop=app_loop) as session:
        snapshot_client = SnapshotHttpClient(session)
        for product in app_config.subscribed_product_ids:
            event_reader = Pipeline(asyncio.Queue())
            product_event_readers[product] = event_reader
            orderbook = Orderbook(event_reader, l2_writer_pipeline, snapshot_client, product,
                                  app_config.num_output_levels, app_config.error_threshold)
            consume_task = asyncio.ensure_future(start_orderbook_consume(orderbook))
            tasks.append(consume_task)
        event_feed = get_full_feed(session, EventDispatcher(product_event_readers),
                                   app_config.full_feed_subscribe_msg)
        start_feed_task = asyncio.ensure_future(start_event_reader(event_feed))
        tasks.append(start_feed_task)
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.create_task(start_app(loop))
    loop.run_forever()
