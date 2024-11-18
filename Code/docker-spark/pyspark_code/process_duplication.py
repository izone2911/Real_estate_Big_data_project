import pyspark.sql.functions as f
from pyspark.sql.functions import udf
from pyspark.ml.feature import Tokenizer, HashingTF, IDF, MinHashLSH
from pyspark.ml.linalg import Vectors, VectorUDT

@udf(returnType=VectorUDT())
def append_non_zero_to_vector(vector, append_value=0.1):
    new_vector_dim = len(vector) + 1
    new_vector_indices = list(vector.indices) + [len(vector)]
    new_vector_values = list(vector.values) + [append_value]
    new_vector = Vectors.sparse(new_vector_dim,
                                new_vector_indices,
                                new_vector_values)
    return new_vector

def get_text_tfidf_vectors(df):
    df = df.withColumn("text", f.concat_ws(" ", f.col("title"), f.col("description"), f.col("address.full_address")))

    # Calculate TF-IDF vectors
    tokenizer = Tokenizer(inputCol="text", outputCol="tokens")
    df = tokenizer.transform(df)
    hashingTF = HashingTF(inputCol="tokens", outputCol="tf")
    df = hashingTF.transform(df)
    idf = IDF(inputCol="tf", outputCol="tfidf")
    idf_model = idf.fit(df)
    df = idf_model.transform(df)
    # Append non-zero value to vectors
    df = df = df.withColumn("text_vector", append_non_zero_to_vector(f.col("tfidf"), f.lit(0.1)))
    return df.drop("text", "tokens", "tf", "tfidf")

def get_duplicate_df_with_minhash(df, threshhold=0.5, num_hash_tables=3, dist_col="distCol"):
    # df must already have "id" column
    minhashLSH = MinHashLSH(inputCol="text_vector", outputCol="hashes", numHashTables=num_hash_tables)
    model = minhashLSH.fit(df)
    duplicate_df = model.approxSimilarityJoin(df.select("id", "text_vector"), df.select("id", "text_vector"), 0.8, distCol=dist_col) \
                         .filter("datasetA.id < datasetB.id")  # Avoid comparing a row to itself
    duplicate_df = duplicate_df.withColumn("id", f.col("datasetA.id")) \
                               .withColumn("duplicate_with_id", f.col("datasetB.id")) \
                               .select("id", "duplicate_with_id", dist_col)
    return duplicate_df

def remove_duplicated_rows(df, remove_ids):
    # df must already have "id" column
    remove_ids = remove_ids.select("id")
    result_df = df.join(remove_ids, df["id"] == remove_ids["id"], "leftanti")
    return result_df

