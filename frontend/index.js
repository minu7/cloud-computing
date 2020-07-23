const signale = require('signale');
const kafka = require('kafka-node');
const app = require('express')();
const { v4: uuidv4 } = require('uuid');
const Consumer = kafka.Consumer;
const Producer = kafka.Producer;

const client = new kafka.KafkaClient({ kafkaHost: 'kafka:9092' });

const requests = {};
client.createTopics([{ topic: 'response', partitions: 1, replicationFactor: 1  }], (err) => {
  if (err) {
    throw err;
  }

  const consumer = new Consumer(
    client,
      [
        { topic: 'response' }
      ],
    {
        autoCommit: true,
        fromOffset: "earliest"
    }
  );
  
  signale.debug('creating consumer');
  consumer.on('message', (message) => {
    // signale.debug(message);
    const value = JSON.parse(message.value);
    if (!requests[value.id]) {
      signale.fatal('Error: request id not present');
      return;
    }
    // signale.debug(value);
    requests[value.id].res.send(value.documents);
    delete requests[value.id];
    return;
  });
});

signale.debug('creating producer');
const producer = new Producer(client, { partitionerType: 2 });
producer.on('ready', () => {
  signale.debug('producer ready');

  client.createTopics([{ topic: 'request', partitions: 3, replicationFactor: 1  }], (err) => {
    if (err) {
      throw err;
    }
    app.get('/bitcoin', (req, res) => {
      id = uuidv4();
      requests[id] = {req, res};
      producer.send([{
        topic: 'request',
        messages: JSON.stringify({
          body: req.body,
          time: new Date(),
          id,
          type: req.query.operation || 'get',
        })
      }], (err, data) => {
        signale.debug(data);
        if (err) {
          signale.fatal(err);
        }
      });
    });

    app.listen(80, () => {
      signale.debug('frontend running on port 80');
      client.refreshMetadata(['request'], (err) => {
        if (err) {
          throw err;
        }
      });
    });  
  });
});

producer.on('error', (err) => {
    signale.fatal('error: ' + err);
    process.exit(1);
});
