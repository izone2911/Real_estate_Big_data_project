import os
import sys
os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages org.elasticsearch:elasticsearch-spark-30_2.12:7.12.0,commons-httpclient:commons-httpclient:3.1 pyspark-shell'

import pyspark
from pyspark.sql import SparkSession
import pyspark.sql.functions as f

from process_duplication import *
from process_text import *
from process_number import *
from process_extra_infos import *

spark = SparkSession.builder.getOrCreate()


# Load files from HDFS
hdfs_file_path = [
    # 'hdfs://192.168.102.7:10000/haihp02/real_estate_data/bds.jsonl',
    # 'hdfs://192.168.102.7:10000/haihp02/real_estate_data/i-batdongsan.jsonl',
    # 'hdfs://192.168.102.7:10000/haihp02/real_estate_data/nhadatviet.jsonl',
    'hdfs://20.239.82.205:10000/haihp02/real_estate_data/test.jsonl'
]
df = spark.read \
    .option("spark.hadoop.fs.defaultFS", "hdfs://20.239.82.205:10000") \
    .json(hdfs_file_path)
print("Done loading.")

# Add index
df = df.withColumn('id', f.monotonically_increasing_id())

# Duplicate processing
# df = get_text_tfidf_vectors(df)
# duplicate_df = get_duplicate_df_with_minhash(df)
# df = remove_duplicated_rows(df=df, remove_ids=duplicate_df)
# print("Duplicated rows removed.")

# Text processing
special_chars_list = list(get_special_chars(df))
df = df.withColumn("title", remove_special_chars("title", f.lit(special_chars_list)))
df = df.withColumn("description", remove_special_chars("description", f.lit(special_chars_list)))
df = df.withColumn("title", remove_duplicate_punctuation_sequence("title"))
df = df.withColumn("description", remove_duplicate_punctuation_sequence("description"))
df = df.withColumn("estate_type", normalize_estate_type("estate_type"))
print("Text processed.")

# Numbers processing
df = df.withColumn("price/square", f.col("price")/f.col("square"))
df = df.withColumn("price", price_normalize("price", "square"))
price_over_square_bound_by_estate_type_df = get_detail_lower_upper_bound(
    df, col_name="price/square",
    lower_percent=5, upper_percent=95, outlier_threshold=5
)
df = filter_with_detail_bound(df, price_over_square_bound_by_estate_type_df,
                              join_col_name="estate_type", filter_col_name="price/square")
print("Numbers processed.")

# Extra infos processing
old_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chổ để xe hơi', 'Hướng', 'Loại tin', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ :', 'Số toilet :', 'Tầng :']
new_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chỗ để xe hơi', 'Hướng', 'remove', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ', 'Số toilet', 'Tầng']
remove_keys = ['remove']
df = df.withColumn("extra_infos", normalize_extra_infos_dict("extra_infos", f.lit(old_keys), f.lit(new_keys), f.lit(remove_keys)))
print("Extra infos processed.")

# Save output
df.drop("id")
# Save to HDFS
# output_path = 'hdfs://10.134.116.27:10000/haihp02/real_estate_data/processed_test.jsonl'
# df.write.json(output_path, mode="overwrite")
# print(f"Output saved to HDFS at: {output_path}")
# Save to elasticsearch
es_config = {
    "es.nodes": "192.168.102.7",
    "es.port": "9200",
    "es.resource": "haihp02_test_index_6",
    "es.nodes.wan.only": "true",
    "es.nodes.discovery": "false"
}
df.write.format("org.elasticsearch.spark.sql") \
    .option("es.nodes", es_config["es.nodes"]) \
    .option("es.port", es_config["es.port"]) \
    .option("es.resource", es_config["es.resource"]) \
    .option("es.nodes.wan.only", es_config["es.nodes.wan.only"]) \
    .option("es.nodes.discovery", es_config["es.nodes.discovery"]) \
    .save()

spark.stop()