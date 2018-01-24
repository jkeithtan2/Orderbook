import concurrent
import logging
import json
import aiofiles as aiofiles
import aiohttp

from enum import Enum, auto

from tenacity import retry, retry_if_exception_type, stop_after_attempt

from src import app_config
from src.exceptions import SnapshotHttpException, SocketException


# @retry(retry=retry_if_exception_type(SocketException),
#        stop=stop_after_attempt(LocalConfig.ws.get('attempts')))
async def get_full_feed(session, dispatcher, sub_msg):
    if not dispatcher or not sub_msg or not session:
        raise ValueError('full feed requires params (session, output_pipes and sub_msg')
    async with session.ws_connect(app_config.ws.get('endpoint')) as ws:
        logging.info('sending sub message {}'.format(sub_msg))
        await ws.send_json(sub_msg)
        sub_confirmation = await ws.receive_json()
        if sub_confirmation.get('type') == 'error':
            raise SocketException('error get subscriptions {}'.format(sub_confirmation))
        if sub_confirmation.get('type') == 'subscriptions' and sub_msg['channels'] == sub_confirmation['channels']:
            async for feed in ws:
                await dispatcher.dispatch(json.loads(feed.data))
        else:
            raise SocketException('Unable to subscribe to full channels')


class SnapshotHttpClient:
    def __init__(self, session):
        self.session = session

    @retry(retry=retry_if_exception_type(SnapshotHttpException),
           stop=stop_after_attempt(app_config.http.get('attempts')))
    async def get_orderbook_snapshot(self, product_id, http_timeout):
        url = app_config.http.get('snapshot_endpoint').format(product_id)
        try:
            async with self.session.get(url, timeout=http_timeout) as resp:
                assert resp.status == 200
                return await resp.json()
        except (concurrent.futures.TimeoutError, aiohttp.ClientError, AssertionError) as e:
            raise SnapshotHttpException(e)


class Pipeline:
    class states(Enum):
        NOT_STARTED = auto()
        STARTED = auto()
        STOP_SENDING = auto()
        CLOSING_PIPE = auto()

    def __init__(self, pipe):
        self.pipe = pipe
        self.state = self.states.NOT_STARTED


async def write_to_stdout(pipeline):
    while True:
        output = await pipeline.pipe.get()
        print(output)

# async def write_to_file(pipeline, file_path):
#     while True:
#         try:
#             async with aiofiles.open(file_path, 'w') as output_file:
#                 output = await pipeline.pipe.get()
#                 await output_file.write(output)
#                 await output_file.flush()
#         except Exception as e:
#             logging.error(e)
