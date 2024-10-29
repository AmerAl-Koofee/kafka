import sys
import six
sys.modules['kafka.vendor.six.moves'] = six.moves


from kafka import KafkaProducer
import requests
import json
import time


producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# CoinGecko API URL för kryptovalutapriser
url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd'


while True:
    response = requests.get(url)
    if response.status_code == 200:
        price_data = response.json()
        print(f'Skickar: {price_data}')
        producer.send('crypto-prices', value=price_data)
    else:
        print(f'Fel vid hämtning av data: {response.status_code}')
    
    time.sleep(20)

producer.flush()
producer.close()