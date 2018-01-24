import logging

from src.event.metadata import EventKeys
from src.io.io_interfaces import Pipeline


class EventDispatcher:
    def __init__(self, pipelines):
        self.pipelines = pipelines or {}

    async def dispatch(self, event):
        pipeline = self.pipelines.get(event.get(EventKeys.PRODUCT_ID))
        if pipeline is not None:
            if pipeline.state == Pipeline.states.NOT_STARTED:
                pipeline.state = Pipeline.states.STARTED
                await pipeline.pipe.put(Pipeline.states.STARTED)
            if pipeline.state is not Pipeline.states.STOP_SENDING:
                await pipeline.pipe.put(event)
        else:
            logging.error("Pipe doesn't exist for {}".format(event))