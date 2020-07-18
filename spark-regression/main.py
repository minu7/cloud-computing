# import sys
# from pyspark.streaming import StreamingContext
# from pyspark.streaming.kafka import KafkaUtils
# from pyspark import SparkContext
# if __name__ == "__main__":
#     sc = SparkContext(appName="PythonStreamingDirect")
#     ssc = StreamingContext(sc, 2)
#     brokers, topic = sys.argv[1:]
#     kvs = KafkaUtils.createDirectStream(
#         ssc, [topic], {"metadata.broker.list": brokers})
#     lines = kvs.map(lambda x: x[1])

#     lines.pprint()
#     ssc.start()
#     ssc.awaitTermination()
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import json
sc = SparkContext('local')
spark = SparkSession(sc)
schema = StructType([ StructField("value", FloatType(), True), StructField("time", TimestampType(), True), ])

spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", "kafka:9092") \
  .option("subscribe", "bitcoin") \
  .option("startingOffsets", "earliest") \
  .load() \
  .selectExpr("CAST(value AS STRING) as json", "CAST(timestamp AS TIMESTAMP) as timestamp") \
  .select('*', from_json(col("json"), schema).alias("parsed")) \
  .select('parsed.value', 'parsed.time') \
  .withWatermark("time", "400 minutes") \
  .groupBy(window('time', '1 minutes')) \
  .count() \
  .writeStream.outputMode("Append").format("console").start().awaitTermination()




#   .writeStream \
#   .format("kafka") \
#   .option("kafka.bootstrap.servers", "kafka:9092") \
#   .option("topic", "bitcoin_res") \
#   .option("checkpointLocation", "/tmp/vaquarkhan/checkpoint") \
#   .trigger(continuous="25 second") \
#   .start() \
#   .awaitTermination()