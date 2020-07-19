const signale = require('signale');
const WebSocket = require('ws');
const kafka = require('kafka-node');

const Producer = kafka.Producer;
const client = new kafka.KafkaClient({ kafkaHost: 'kafka:9092' });
const producer = new Producer(client);

producer.on('ready', () => {
  const pricesWs = new WebSocket('wss://ws.coincap.io/prices?assets=ALL');

  pricesWs.onmessage = data => {
  const prices = JSON.parse(data.data);
    if (prices['bitcoin']) {
      producer.send([{
        topic: 'bitcoin',
        messages: JSON.stringify({
          value: Number(prices['bitcoin']),
          time: new Date()
        })
      }], (err, data) => {
        // signale.debug(data);
        if (err) {
          signale.fatal(err);
        }
      });
    }
  };
});

producer.on('error', function (err) {
  signale.fatal('error: ' + err);
  process.exit(1);
});
