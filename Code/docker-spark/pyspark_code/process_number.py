import pyspark.sql.functions as f
from pyspark.sql.functions import udf
from pyspark.sql.types import FloatType
import underthesea
import numpy as np

from type_cast import *

def get_lower_upper_bound(df, col_name, lower_percent=5, upper_percent=95, outlier_threshold=5):
    lower_percentile, upper_percentile = df.approxQuantile(col_name, [lower_percent/100, upper_percent/100], 0.01)
    quantile_range = upper_percentile - lower_percentile
    lower_bound = np.max([0, lower_percentile - outlier_threshold * quantile_range])
    upper_bound = upper_percentile + outlier_threshold * quantile_range
    return lower_bound, upper_bound

def get_detail_lower_upper_bound(df, col_name, lower_percent=5, upper_percent=95, outlier_threshold=5):
    quantiles_by_estate_type = (
        df.groupBy("estate_type")
        .agg(f.percentile_approx(col_name, [lower_percent/100, upper_percent/100], 100).alias("percentile_approx"))
    )
    quantiles_by_estate_type = quantiles_by_estate_type.withColumn("lower_percentile", f.col("percentile_approx").getItem(0)) \
                                                       .withColumn("upper_percentile", f.col("percentile_approx").getItem(1)) \
                                                       .withColumn("quantile_range", f.col("upper_percentile") - f.col("lower_percentile"))
    quantiles_by_estate_type = quantiles_by_estate_type.withColumn("lower_bound", f.greatest(f.col("lower_percentile") - outlier_threshold * f.col("quantile_range"), f.lit(0))) \
                                                       .withColumn("upper_bound", f.col("upper_percentile") + outlier_threshold * f.col("quantile_range"))
    
    return quantiles_by_estate_type.select("estate_type", "lower_bound", "upper_bound")

def filter_with_detail_bound(df, bound_df, join_col_name, filter_col_name):
    join_df = df.join(bound_df.alias("bound_df"), join_col_name, "inner")
    filtered_df = join_df.filter((join_df[filter_col_name] >= join_df["lower_bound"]) \
                                 & (join_df[filter_col_name] <= join_df["upper_bound"]))
    return filtered_df.drop("lower_bound", "upper_bound")

@udf(returnType=FloatType())
def price_normalize(price, square):
    if price is None:
        return None
    if isinstance(price, int) or isinstance(price, float):
        return price
    elif isinstance(price, str):
        if cast_to_float(price) is not None:
            return cast_to_float(price)
        if square is not None:
            price = underthesea.text_normalize(price)
            # Các trường hợp thực sự điền giá / m2
            if 'triệu/ m' in price or 'triệu / m' in price:
                price = float(price.split()[0]) * 1e6 * square
            # Các trường hợp điền nhầm giá sang giá / m2
            elif 'tỷ/ m' in price or 'tỷ / m' in price:
                price = float(price.split()[0]) * 1e9
            else:
                price = None
        elif square is None:
            price = None
    return price