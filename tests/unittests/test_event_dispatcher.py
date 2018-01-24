import asyncio
import unittest

from src.io.dispatchers import EventDispatcher
from src.io.io_interfaces import Pipeline


class TestEventDispatcher(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.pipeline_1 = Pipeline(asyncio.Queue())
        self.pipeline_2 = Pipeline(asyncio.Queue())
        self.pipelines = {'1': self.pipeline_1, '2': self.pipeline_2}
        self.eventdispatcher = EventDispatcher(self.pipelines)

    def test_events_should_dispatch_to_correct_pipelines(self):
        events = [{'product_id': '1'}, {'product_id': '2'}, {'product_id': '1'}]

        async def test_runner():
            pipe_1_events = []
            pipe_2_events = []
            for event in events:
                await self.eventdispatcher.dispatch(event)
            while self.pipeline_1.pipe.empty() is False:
                pipe_1_events.append(await self.pipeline_1.pipe.get())
            while self.pipeline_2.pipe.empty() is False:
                pipe_2_events.append(await self.pipeline_2.pipe.get())
            self.assertEqual([Pipeline.states.STARTED, {'product_id': '1'}, {'product_id': '1'}], pipe_1_events)
            self.assertEqual([Pipeline.states.STARTED, {'product_id': '2'}], pipe_2_events)

        self.loop.run_until_complete(test_runner())

    def test_only_pipe_1_should_have_events(self):
        events = [{'product_id': '1'}, {'product_id': '3'}, {'product_id': '1'}]

        async def test_runner():
            pipe_1_events = []
            with self.assertLogs(level='WARNING') as cm:
                for event in events:
                    await self.eventdispatcher.dispatch(event)
                while self.pipeline_1.pipe.empty() is False:
                    pipe_1_events.append(await self.pipeline_1.pipe.get())
                self.assertEqual([Pipeline.states.STARTED, {'product_id': '1'}, {'product_id': '1'}], pipe_1_events)
            self.assertEqual("ERROR:root:Pipe doesn't exist for {'product_id': '3'}", cm.output[0])

        self.loop.run_until_complete(test_runner())
