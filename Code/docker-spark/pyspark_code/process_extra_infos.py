import pyspark.sql.functions as f
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType, IntegerType, FloatType, StructType, StructField, BooleanType

from type_cast import *

def get_extra_info_labels(df):
    extra_infos_df = df.select("extra_infos")
    extra_infos_labels = extra_infos_df.rdd.flatMap(lambda x: list(x[0].asDict().keys())).collect()
    return set(extra_infos_labels)
    
def normalize_text_field_in_dict(dict_obj):
    result_dict = dict_obj
    for key in result_dict.keys():
        if isinstance(result_dict[key], str):
            result_dict[key] = result_dict[key].replace(',', '.')
            new_val = ''
            for c in result_dict[key]:
                if c.isalpha() or c.isnumeric() or c == '.' or c == ' ':
                    new_val += c
            result_dict[key] = new_val
    return result_dict

@udf(returnType=StructType([
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