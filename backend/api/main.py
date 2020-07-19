from kafka import KafkaConsumer
from kafka import KafkaProducer
from bson.json_util import dumps
import logging
import json
import pymongo

print("starting backend")
myclient = pymongo.MongoClient("mongodb://root:password@mongo:27017/")
mydb = myclient["admin"]
candlesticks = mydb['candlesticks']
producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    client_id='backend',
    api_version=(0, 10, 1),
    value_serializer=lambda m: json.dumps(m).encode('ascii')
)

consumer = KafkaConsumer(
    'request', 
    bootstrap_servers='kafka:9092', 
    value_deserializer=lambda m: json.loads(m.decode('ascii')),
    api_version=(0, 10, 1),
    group_id='backend'
)


for msg in consumer:
    print(msg.value)
    documents = candlesticks.find({}, sort=[( '_id', pymongo.DESCENDING )])
    documents = [d for d in documents]
    msg.value["documents"] = dumps(documents) 
    print(producer.send('response', value=msg.value).get(timeout=30))
