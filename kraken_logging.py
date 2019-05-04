order_id = order['result']['txid'][0]
history = k.get_trades_history()[0]
order_info = history[history['ordertxid'] == order_id]
