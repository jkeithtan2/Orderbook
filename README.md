pip install -r requirements.txt before running on virtualenv



modify subscribed_product_ids in app_config.py to subscirbe to different products



modify error_threshold to change how much error an orderbook can tolerate before it needs to be rebuilt



modify http = {
    "attempts": 5,
    "timeout": 30,
    "snapshot_endpoint": "https://api.gdax.com/products/{}/book?level=3"
} 

to modify http retry conditions



modify num_output_levels to change the top X amount of the orderbook



Let me know if packaging does not work. Project migrated to github
