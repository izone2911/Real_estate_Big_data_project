import os
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.elasticsearch:elasticsearch-spark-30_2.12:7.12.0,commons-httpclient:commons-httpclient:3.1,org.apache.spark:spark-streaming-kafka-0-10_2.12:3.0.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.0.0 pyspark-shell'
import sys
import string
import re

import pyspark
from pyspark.sql import SparkSession
import pyspark.sql.functions as f
from pyspark.sql.types import StringType, FloatType, StructType, StructField, BooleanType, IntegerType, ArrayType, DoubleType
import underthesea
import numpy as np
from process_duplication import *
from process_text import *
from process_number import *
from process_extra_infos import *


spark = SparkSession.builder.master("local[1]").getOrCreate()
# spark.sparkContext.setLogLevel("ERROR")

# Set up data stream
kafka_config = {
    "kafka.bootstrap.servers": "20.239.82.205:9192,20.239.82.205:9292,20.239.82.205:9392",
    "subscribe": "bds,i-batdongsan,nhadatviet,test",
    "startingOffsets": "latest"
}
streaming_df = spark \
  .readStream \
  .format("kafka") \
  .option("kafka.bootstrap.servers", kafka_config["kafka.bootstrap.servers"]) \
  .option("subscribe", kafka_config["subscribe"]) \
  .option("startingOffsets", kafka_config["startingOffsets"]) \
  .load()

# Predefined object from collected data
special_chars_list = ['→', '\u202a', '\uf0d8', '✤', '\u200c', 'ۣ', '🅖', '–', '₋', '●', '¬', '̶', '▬', '≈', '🫵', '◇', '▷', '🪷', '◊', '‐', '🫴', '\uf05b', '⦁', '️', '㎡', '🫰', '′', '✥', '✧', '♤', '🫶', 'ۜ', '❃', '̀', '֍', '\u2060', '\u206e', '‘', '❈', '🅣', '🅘', '℅', '\ufeff', '″', '\u200b', '♚', '̣', '₫', '\uf06e', '✩', '🅨', '’', '\xad', '★', '±', '\U0001fae8', '︎', '\uf0f0', '∙', '♛', '̉', '̛', '❆', '✜', '÷', '♜', '·', '❖', '】', '❁', '🫱', '・', '€', '☛', '“', '■', '\uf046', '￼', '�', '\u200d', '🫠', '\uf0e8', '⁃', '≥', '～', '➣', '́', '🪩', '̃', '\uf02b', '᪥', '🪺', '♧', '❂', '。', '♡', '，', '🪸', '：', '¥', '❝', '̂', '\U0001fa77', '\uf0a7', 'ৣ', '⚘', '➢', '⇔', '、', '－', '✆', '🫣', '⛫', '►', '̆', '✎', '❯', '《', '\uf076', '❮', '❀', '̵', '🥹', '❉', '̷', '\uf028', '✽', '«', '⇒', '➤', '\uf0e0', '\U0001faad', '♙', '\uf0fc', '【', '➥', '¤', '＆', '🛇', '\x7f', '）', '—', '”', '❞', '》', '☆', '×', '✞', '✿', '≤', '🅐', '√', '°', '✓', '¡', '…', '•', '»', '❊', '➦', '\u06dd', '\uf06c', '¸']
old_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chổ để xe hơi', 'Hướng', 'Loại tin', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ :', 'Số toilet :', 'Tầng :']
new_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chỗ để xe hơi', 'Hướng', 'remove', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ', 'Số toilet', 'Tầng']
remove_keys = ['remove']

schema = StructType([
    StructField("address", StructType([
        StructField("district", StringType(), nullable=True),
        StructField("full_address", StringType(), nullable=True),
        StructField("province", StringType(), nullable=True),
        StructField("ward", StringType(), nullable=True),
    ]), nullable=True),
    StructField("contact_info", StructType([
        StructField("name", StringType(), nullable=True),
        StructField("phone", ArrayType(StringType()), nullable=True),
    ]), nullable=True),
    StructField("description", StringType(), nullable=True),
    StructField("estate_type", StringType(), nullable=True),
    StructField("extra_infos", StructType([
        StructField("Chiều dài", StringType(), nullable=True),
        StructField("Chiều ngang", StringType(), nullable=True),
        StructField("Chính chủ", BooleanType(), nullable=True),
        StructField("Chổ để xe hơi", BooleanType(), nullable=True),
        StructField("Hướng", StringType(), nullable=True),
        StructField("Loại tin", StringType(), nullable=True),
        StructField("Lộ giới", StringType(), nullable=True),
        StructField("Nhà bếp", BooleanType(), nullable=True),
        StructField("Pháp lý", StringType(), nullable=True),
        StructField("Phòng ăn", BooleanType(), nullable=True),
        StructField("Sân thượng", BooleanType(), nullable=True),
        StructField("Số lầu", StringType(), nullable=True),
        StructField("Số phòng ngủ", StringType(), nullable=True),
        StructField("Số phòng ngủ :: string", StringType(), nullable=True),
        StructField("Số toilet :: string", StringType(), nullable=True),
        StructField("Tầng :: string", StringType(), nullable=True),
    ]), nullable=True),
    StructField("link", StringType(), nullable=True),
    StructField("post_date", StringType(), nullable=True),
    StructField("post_id", StringType(), nullable=True),
    StructField("price", StringType(), nullable=True),
    StructField("square", DoubleType(), nullable=True),
    StructField("title", StringType(), nullable=True),
])

json_string_df = streaming_df.selectExpr("CAST(value AS STRING) as json_string")
# Use the predefined schema from colected data
parsed_json_df = json_string_df.select(
    f.from_json("json_string", schema).alias("data")
)
final_df = parsed_json_df.select("data.*")

# Text processing
def remove_special_chars(input_string, special_chars_list, at_once=False):
    if not input_string:
        return None
    if at_once:
        special_chars_string = ''.join()
        translator = str.maketrans('', '', special_chars_string)
        result = input_string.translate(translator)
    else:
        result = input_string
        for c in special_chars_list:
            result = result.replace(c, '')
    return result

def remove_special_chars_uds(special_chars_list):
    return udf(lambda s: remove_special_chars(s, special_chars_list), returnType=StringType())

final_df = final_df.withColumn("title", remove_special_chars_uds(special_chars_list)(f.col("title")))
final_df = final_df.withColumn("description", remove_special_chars_uds(special_chars_list)(f.col("description")))
final_df = final_df.withColumn("title", remove_duplicate_punctuation_sequence("title"))
final_df = final_df.withColumn("description", remove_duplicate_punctuation_sequence("description"))
final_df = final_df.withColumn("estate_type", normalize_estate_type("estate_type"))
print("Text processed.")

# Numbers processing
final_df = final_df.withColumn("price/square", f.col("price")/f.col("square"))
final_df = final_df.withColumn("price", price_normalize("price", "square"))
print("Numbers processed.")

# Extra infos processing
def normalize_extra_infos_dict(input_extra_infos_row, old_keys, new_keys, remove_keys):
    if input_extra_infos_row is None:
        return None
    old_keys = list(old_keys)
    new_keys = list(new_keys)
    remove_keys = list(remove_keys)
    assert len(old_keys) == len(new_keys)

    # Normalize dict keys
    extra_infos_dict = input_extra_infos_row.asDict()
    dict_nomalized_keys = {k: None for k in new_keys}

    for old_key, new_key in zip(old_keys, new_keys):
        if old_key in extra_infos_dict.keys():
            if new_key in dict_nomalized_keys.keys() and dict_nomalized_keys[new_key] is None \
                or new_key not in dict_nomalized_keys.keys():
                dict_nomalized_keys[new_key] = extra_infos_dict[old_key]
        else:
            dict_nomalized_keys[new_key] = None
    for key in remove_keys:
        if key in dict_nomalized_keys.keys():
            dict_nomalized_keys.pop(key)
    # Normalize dict values
    result_dict = normalize_text_field_in_dict(dict_nomalized_keys)
    result_dict['Chiều dài'] = cast_to_float(dict_nomalized_keys['Chiều dài'].replace('m', '')) if result_dict['Chiều dài'] is not None else None
    result_dict['Chiều ngang'] = cast_to_float(dict_nomalized_keys['Chiều ngang'].replace('m', '')) if result_dict['Chiều ngang'] is not None else None
    result_dict['Chính chủ'] = cast_to_boolean(dict_nomalized_keys['Chính chủ']) if result_dict['Chính chủ'] is not None else None
    result_dict['Chỗ để xe hơi'] = cast_to_boolean(dict_nomalized_keys['Chỗ để xe hơi']) if result_dict['Chỗ để xe hơi'] is not None else None
    result_dict['Hướng'] = cast_to_string(dict_nomalized_keys['Hướng']) if result_dict['Hướng'] is not None else None
    result_dict['Lộ giới'] = cast_to_float(dict_nomalized_keys['Lộ giới'].replace('m', '')) if result_dict['Lộ giới'] is not None else None
    result_dict['Nhà bếp'] = cast_to_boolean(dict_nomalized_keys['Nhà bếp']) if result_dict['Nhà bếp'] is not None else None
    result_dict['Pháp lý'] = cast_to_string(dict_nomalized_keys['Pháp lý']) if result_dict['Pháp lý'] is not None else None
    result_dict['Phòng ăn'] = cast_to_boolean(dict_nomalized_keys['Phòng ăn']) if result_dict['Phòng ăn'] is not None else None
    result_dict['Sân thượng'] = cast_to_boolean(dict_nomalized_keys['Sân thượng']) if result_dict['Sân thượng'] is not None else None
    result_dict['Số lầu'] = cast_to_integer(dict_nomalized_keys['Số lầu']) if result_dict['Số lầu'] is not None else None
    result_dict['Số phòng ngủ'] = cast_to_integer(dict_nomalized_keys['Số phòng ngủ']) if result_dict['Số phòng ngủ'] is not None else None
    result_dict['Số toilet'] = cast_to_integer(dict_nomalized_keys['Số toilet']) if result_dict['Số toilet'] is not None else None
    result_dict['Tầng'] = cast_to_integer(dict_nomalized_keys['Tầng']) if result_dict['Tầng'] is not None else None
    return result_dict

def normalize_extra_infos_dict_udf(old_keys, new_keys, remove_keys):
    return udf(lambda d: normalize_extra_infos_dict(d, old_keys, new_keys, remove_keys),returnType=StructType([
    StructField('Chiều dài', FloatType()),
    StructField('Chiều ngang', FloatType()),
    StructField('Chính chủ', BooleanType()),
    StructField('Chỗ để xe hơi', BooleanType()),
    StructField('Hướng', StringType()),
    StructField('Lộ giới', FloatType()),
    StructField('Nhà bếp', BooleanType()),
    StructField('Pháp lý', StringType()),
    StructField('Phòng ăn', BooleanType()),
    StructField('Sân thượng', BooleanType()),
    StructField('Số lầu', IntegerType()),
    StructField('Số phòng ngủ', IntegerType()),
    StructField('Số toilet', IntegerType()),
    StructField('Tầng', IntegerType()),
]))

final_df = final_df.withColumn("extra_infos", normalize_extra_infos_dict_udf(old_keys, new_keys, remove_keys)(f.col("extra_infos")))
print("Extra infos processed.")

# Output two queries, one to console and one to elasticsearch
console_query = final_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

es_config = {
    "es.nodes": "20.239.82.205",
    "es.port": "9200",
    "es.resource": "haihp02_test_streaming_index",
    "es.nodes.wan.only": "true",
    "es.nodes.discovery": "false"
}
elasticsearch_query = final_df.writeStream \
    .outputMode("append") \
    .format("org.elasticsearch.spark.sql") \
    .option("es.nodes", es_config["es.nodes"]) \
    .option("es.port", es_config["es.port"]) \
    .option("es.resource", es_config["es.resource"]) \
    .option("es.nodes.wan.only", es_config["es.nodes.wan.only"]) \
    .option("es.nodes.discovery", es_config["es.nodes.discovery"]) \
    .option("checkpointLocation", "./elasticsearch_log_checkpoint") \
    .start()

console_query.awaitTermination()
elasticsearch_query.awaitTermination()

spark.stop()
