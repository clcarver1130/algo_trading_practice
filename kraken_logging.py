order_id = order['result']['txid'][0]
history = k.get_trades_history()[0]
order_info = history[history['ordertxid'] == order_id]


df = k.get_trades_history(start=1556999665, end=1557345265)[0]
df2 = df[['cost', 'fee', 'margin', 'price', 'type', 'vol']]
df_trades = df2.add_suffix('_buy').join(df2.shift(-1).add_suffix('_sell'))
df_trades[df_trades['type_buy'] == 'buy']
