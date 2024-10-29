import sys
import six
sys.modules['kafka.vendor.six.moves'] = six.moves

import joblib
from collections import deque
from datetime import datetime
import matplotlib.pyplot as plt
from kafka import KafkaConsumer
import json

# Ladda de tränade modellerna för både Bitcoin och Ethereum
model_bitcoin = joblib.load('bitcoin_price_predictor.pkl')
model_ethereum = joblib.load('ethereum_price_predictor.pkl')

# Buffer för senaste prisdata som används för prediktion (historik)
n = 10  # Antal datapunkter som används i modellerna
prediction_offset = 10  # Förskjutning av prediktioner med 10 steg framåt
bitcoin_history = deque(maxlen=n)
ethereum_history = deque(maxlen=n)

# Skapa Kafka-konsumenten
consumer = KafkaConsumer(
    'crypto-prices',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Buffertar för prisdata och tidsstämplar
bitcoin_prices = deque(maxlen=100)  # För faktiska värden
ethereum_prices = deque(maxlen=100)
predicted_bitcoin_prices = deque(maxlen=100)  # För förväntade värden
predicted_ethereum_prices = deque(maxlen=100)
timestamps_actual = deque(maxlen=100)
timestamps_predicted = deque(maxlen=100)

# Slå på interaktivt läge
plt.ion()
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Initialiserar linjerna för att kunna uppdatera dem
line_bitcoin_actual, = ax1.plot([], [], label="Bitcoin Faktiskt", color="blue")
line_bitcoin_pred, = ax1.plot([], [], label="Bitcoin Förväntat", color="red", linestyle='--')
line_ethereum_actual, = ax2.plot([], [], label="Ethereum Faktiskt", color="green")
line_ethereum_pred, = ax2.plot([], [], label="Ethereum Förväntat", color="orange", linestyle='--')

ax1.set_title("Bitcoin prisutveckling")
ax1.set_ylabel("Pris i USD")
ax1.legend()

ax2.set_title("Ethereum prisutveckling")
ax2.set_xlabel("Tid")
ax2.set_ylabel("Pris i USD")
ax2.legend()

try:
    for i, message in enumerate(consumer):
        crypto_data = message.value
        bitcoin_price = crypto_data['bitcoin']['usd']
        ethereum_price = crypto_data['ethereum']['usd']

        # Uppdatera historikbuffertar för att kunna göra nya prediktioner
        bitcoin_history.append(bitcoin_price)
        ethereum_history.append(ethereum_price)

        # Lägg till de faktiska priserna och tidsstämplar
        bitcoin_prices.append(bitcoin_price)
        ethereum_prices.append(ethereum_price)
        timestamps_actual.append(datetime.now().strftime('%H:%M:%S'))

        # Gör förutsägelser och fördröj dem med 10 steg om vi har tillräckligt många historikpunkter
        if len(bitcoin_history) == n:
            prediction_bitcoin = model_bitcoin.predict([list(bitcoin_history)])[0]
            predicted_bitcoin_prices.append(prediction_bitcoin)
            timestamps_predicted.append(datetime.now().strftime('%H:%M:%S'))
            print(f"Förväntat Bitcoin-pris nästa datapunkt: {prediction_bitcoin}")

        if len(ethereum_history) == n:
            prediction_ethereum = model_ethereum.predict([list(ethereum_history)])[0]
            predicted_ethereum_prices.append(prediction_ethereum)
            print(f"Förväntat Ethereum-pris nästa datapunkt: {prediction_ethereum}")

        # Bestäm minsta gemensamma längd för att undvika mismatch vid plotting
        min_len_actual = min(len(timestamps_actual), len(bitcoin_prices), len(ethereum_prices))
        min_len_predicted = min(len(timestamps_predicted), len(predicted_bitcoin_prices), len(predicted_ethereum_prices))

        # Sätt data för linjerna
        line_bitcoin_actual.set_data(range(min_len_actual), list(bitcoin_prices)[:min_len_actual])
        line_bitcoin_pred.set_data(range(prediction_offset, prediction_offset + min_len_predicted), list(predicted_bitcoin_prices)[:min_len_predicted])
        line_ethereum_actual.set_data(range(min_len_actual), list(ethereum_prices)[:min_len_actual])
        line_ethereum_pred.set_data(range(prediction_offset, prediction_offset + min_len_predicted), list(predicted_ethereum_prices)[:min_len_predicted])

        # Uppdatera axelns gränser
        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()

        # Visa endast var tionde tidsstämpel för att undvika plottrighet
        displayed_timestamps = [timestamps_actual[i] if i % 10 == 0 else "" for i in range(len(timestamps_actual))]
        ax2.set_xticks(range(len(displayed_timestamps)))
        ax2.set_xticklabels(displayed_timestamps, rotation=45, ha='right')

        plt.tight_layout()
        plt.pause(0.5)

except KeyboardInterrupt:
    print("Avbrutet av användaren.")
finally:
    plt.ioff()
    plt.show()
