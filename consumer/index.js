const signale = require('signale');
const kafka = require('kafka-node');
const MongoClient = require('mongodb').MongoClient;
const uri = "mongodb://root:password@mongo/admin?retryWrites=true&w=majority";
const mongo = new MongoClient(uri, { useNewUrlParser: true });

function start() {
  const Consumer = kafka.Consumer;
  const client = new kafka.KafkaClient({ kafkaHost: 'kafka:9092' });
  const consumer = new Consumer(
      client,
        [
          { topic: 'bitcoin_candlestick' }
        ],
      {
          autoCommit: true,
          fromOffset: "earliest"
      }
    );
  
  mongo.connect(err => {
    if (err) {
      throw err;
    }
    signale.debug("listening on topic bitcoin_candlestick");
    const candlesticks = mongo.db("admin").collection("candlesticks");
    consumer.on('message', (message) => {
      const doc = JSON.parse(message.value);
      signale.debug(doc);
      candlesticks.insertOne(doc, (err) => {
        if (err) throw err;
        signale.debug("INSERTED");
      });
    });
  });
}

setTimeout(start, 15000);