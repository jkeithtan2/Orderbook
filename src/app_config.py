"""
Will be dynamic config in production, for this exercise leave it as a static py file
naming convention is that of a .properties file
"""
from pathlib import Path

num_output_levels = 25

output_path = Path.cwd().joinpath("output\output_stream.txt")

error_threshold = 10

http = {
    "attempts": 5,
    "timeout": 30,
    "snapshot_endpoint": "https://api.gdax.com/products/{}/book?level=3"
}

ws = {
    "attempts": 1,
    "endpoint": "wss://ws-feed.gdax.com"
}

product_list = ['BCH-BTC', 'BCH-USD', 'BTC-EUR', 'BTC-GBP', 'BTC-USD', 'ETH-BTC',
                'ETH-EUR', 'ETH-USD', 'LTC-BTC', 'LTC-EUR', 'LTC-USD', 'BCH-EUR']

subscribed_product_ids = ["ETH-EUR", "BTC-EUR", "BTC-USD", "LTC-BTC"]

full_feed_subscribe_msg = {
    "type": "subscribe",
    "channels": [
        {
            "name": "full",
            "product_ids": subscribed_product_ids
        }
    ]
}


