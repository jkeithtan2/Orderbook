import unittest

from src.event.verifiers import Errors, get_event_format_errors


class TestEventVerifiers(unittest.TestCase):
    def setUp(self):
        self.sample_normal_open_event = {"type": "open",
                                         "side": "buy",
                                         "price": "1707.50000000",
                                         "order_id": "a184603d-3dd3-4e98-93da-f7f2175da77b",
                                         "remaining_size": "0.00783100",
                                         "product_id": "BTC-USD",
                                         "sequence": 4864284473,
                                         "time": "2018-01-15T11:52:58.063000Z"}

        self.sample_normal_done_event = {"type": "done",
                                         "side": "sell",
                                         "order_id": "1c42e338-0f98-4eb3-b6f1-01f87f8dc640",
                                         "reason": "canceled",
                                         "product_id": "BTC-USD",
                                         "price": "13675.70000000",
                                         "remaining_size": "0.00020000",
                                         "sequence": 4864284492,
                                         "time": "2018-01-15T11:52:58.548000Z"
                                         }

    def test_match_event_should_have_no_errors(self):
        errors = get_event_format_errors(self.sample_normal_open_event)
        self.assertEqual([], errors)

    def test_dont_event_should_have_no_errors(self):
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([], errors)

    def test_should_have_no_side_error(self):
        self.sample_normal_done_event['side'] = ''
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([Errors.SIDE_ERROR], errors)

    def test_should_have_side_price_and_size_errors(self):
        self.sample_normal_done_event['side'] = ''
        self.sample_normal_done_event['remaining_size'] = 'abc'
        self.sample_normal_done_event['price'] = 'abc'
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([Errors.SIDE_ERROR,
                          Errors.PRICE_NOT_NUMERIC, Errors.SIZE_NOT_NUMERIC], errors)

    def test_should_have_negative_price_size_errors(self):
        self.sample_normal_done_event['remaining_size'] = '-100.00'
        self.sample_normal_done_event['price'] = '-50.9595'
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([Errors.NEGATIVE_PRICE, Errors.NEGATIVE_SIZE], errors)

    def test_should_have_no_side_nonnumeric_price_and_size_errors(self):
        self.sample_normal_done_event['side'] = ''
        self.sample_normal_done_event['remaining_size'] = ''
        self.sample_normal_done_event['price'] = ''
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([Errors.SIDE_ERROR,
                          Errors.PRICE_NOT_NUMERIC, Errors.SIZE_NOT_NUMERIC], errors)

    def test_should_have_side_nonnumeric_price_negative_size_errors(self):
        self.sample_normal_done_event['side'] = ''
        self.sample_normal_done_event['remaining_size'] = '-0.01'
        self.sample_normal_done_event['price'] = 'asfa214124sf'
        errors = get_event_format_errors(self.sample_normal_done_event)
        self.assertEqual([Errors.SIDE_ERROR,
                          Errors.PRICE_NOT_NUMERIC, Errors.NEGATIVE_SIZE], errors)
