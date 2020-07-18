const signale = require('signale');
const kafka = require('kafka-node');

function start() {
  const Consumer = kafka.Consumer;
  const client = new kafka.KafkaClient({ kafkaHost: 'kafka:9092' });
  const consumer = new Consumer(
      client,
        [
          { topic: 'bitcoin' }
        ],
      {
          autoCommit: true
      }
  );

  consumer.on('message', (message) =>{
    signale.debug(message);
  });
}
setTimeout(start, 15000);
