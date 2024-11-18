import json
import string
import pickle
from tqdm import tqdm
from copy import copy, deepcopy
from random import shuffle
import regex as re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import underthesea

from util import *

TFIDF_VECTORIZER_PATH = './bds_scraper/save/tfidf_model.pkl'

def load_data(file_paths):
    file_paths = list(file_paths)
    data = []
    for file_path in file_paths:
        data.extend(read_json(file_path=file_path, encoding='utf8'))
    return data

# REMOVE DUPLICATE
def remove_duplicated_items(data, vectorizer_path=TFIDF_VECTORIZER_PATH, threshhold=(0.95, 0.98), sample_size=500):
    if (not isinstance(threshhold, tuple)) and (not isinstance(threshhold, list)):
        threshhold = tuple(threshhold, threshhold)
    vectorizer = load_pickle(vectorizer_path)

    represent_items = list()
    all_unique_items = list()

    def _is_similar(saved, candidate, threshhold):
        saved_title = saved['title']
        candidate_title = candidate['title']

        saved_description_vector = saved['description_vector']
        candidate_description_vector = candidate['description_vector']

        similarity = cosine_similarity(saved_description_vector, candidate_description_vector).item()

        is_similar = (saved_title == candidate_title and similarity > threshhold[0]) or similarity > threshhold[1]
        return is_similar, candidate_description_vector

    for i, item in tqdm(enumerate(data)):
        if len(represent_items) > sample_size:
            shuffle(represent_items)
            represent_items = represent_items[:sample_size//2]
        
        candidate = {
            'title': item['title'],
            'description_vector': vectorizer.transform([item['description']]),
            'index': i
        }
        duplicated = False
        for saved_item in represent_items:
            is_similar, candidate_description_vector = _is_similar(saved=saved_item, candidate=candidate)
            if is_similar:
                duplicated = True
                break
        if not duplicated:
            represent_items.append(candidate)
            all_unique_items.append(item)

    return all_unique_items

# TEXT PROCESSING
def get_special_chars(data):
    all_chars = set()
    for item in data:
        if item['title']:
            for c in item['title']:
                all_chars.add(c)
        if item['description']:
            for c in item['description']:
                all_chars.add(c)

    special_chars = set()
    for c in all_chars:
        if not c.isalpha() and not c.inumeric() and not c.isspace() and not c in string.punctuation:
            special_chars.add(c)
    return list[special_chars]
            

def remove_special_chars(item, special_chars):
    item = deepcopy(item)

    def remove_chars(input_string, chars_list, at_once=False):
        if at_once:
            chars_string = ''.join(chars_list)
            translator = str.maketrans("", "", chars_string)
            result = input_string.translate(chars_string)
        else:
            result = copy(input_string)
            for c in chars_list:
                result = result.replace(c, '')
        return result
    
    if item['title']:
        item['title'] = remove_chars(item['title'], special_chars)
    if item['description']:
        item['description'] = remove_chars(item['description'], special_chars)
    
    return item

def remove_duplicate_punctuation_sequence(item):
    item = deepcopy(item)

    def remove_duplicate_sequence(text, target_char, max_length):
        pattern_1 = re.escape(target_char) + '{' + str(max_length) + ',}'
        pattern_2 = '(' + '\s' + re.escape(target_char) + ')' + '{' + str(max_length) + ',}'
        result = re.sub(pattern_2, target_char, re.sub(pattern_1, target_char, text))
        return result
    
    for punc in string.punctuation:
        if punc == '\\':
            continue
        max_length = 3 if punc == '.' else 1
        if item['title']:
            item['title'] = remove_duplicate_sequence(item['title'], punc, max_length)
        if item['description']:
            item['description'] = remove_duplicate_sequence(item['description'], punc, max_length)

    return item

def get_estate_types(data):
    estate_types = set()
    for item in data:
        if item['estate_type']:
            estate_types.append(item['estate_type'])
    return estate_types

def estate_type_normalize(item):
    item = deepcopy(item)

    estate_type_prefix = ['Cho thuể', 'Mua bán', 'Căn hộ']
    estate_type_map = {
        'Biệt thự, liền k`ề': 'Biệt thự liền kề',
        'Nhà biệt thự liền kề': 'Biệt thự liền kề',
        'Nhà mặt phố': 'Nhà mặt tiền',
        'Phòng trọ, nhà trọ, nhà trọ': 'Phòng trọ, nhà trọ',
        'Phòng trọ': 'Phòng trọ, nhà trọ',
        'Trang trại, khu nghỉ dưỡng': 'Trang trại khu nghỉ dưỡng',
        'Kho nhà xưởng': 'Kho xưởng',
        'Kho, xưởng': 'Kho xưởng'
    }

    if item['estate_type']:
        for prefix in estate_type_prefix:
            item['estate_type'] = item['estate_type'].replace(prefix, '').strip().capitalize()
        for estate_type in estate_type_map.keys():
            item['estate_type'] = item['estate_type'].replace(estate_type, estate_type_map[estate_type]).strip().capitalize()

    return item


# NUMERIC PROCESSING
def price_normalize(item):
    item = deepcopy(item)

    if item['square'] is not None and isinstance(item['price'], str):
        item['price'] = underthesea.text_normalize(item['price'])
        if 'triệu/ m' in item['price'] or 'triệu / m' in item['price']:
            item['price'] = float(item['price'].split()[0]) * 1e6 * item['square']
        elif 'tỷ/ m' in item['price'] or 'tỷ / m' in item['price']:
            item['price'] = float(item['price'].split()[0]) * 1e6
        else:
            item['price'] = None
    elif item['square'] is None and isinstance(item['price'], str):
        item['price'] = None

def remove_overpriced_items(data, lower_percent=5, upper_percent=95, outlier_threshold=5, overprice=1e15):
    price_list = list()
    for item in data:
        if item['price']:
            price_list.append(item['price'])
    lower_percentile, upper_percentile = np.percentile(price_list, [upper_percent, lower_percent])
    iqr = upper_percentile - lower_percentile
    lower_bound = np.max(0, lower_percentile - outlier_threshold * iqr)
    upper_bound = upper_percentile + outlier_threshold * iqr

    for item in data:
        if item['price'] and item['price'] > overprice:
            while item['price'] > upper_bound:
                item['price'] /= 1e3

# EXTRA INFOS PROCESSING
def get_all_extra_info_labels(data):
    labels = set()
    for item in data:
        for label in item['extra_infos'].keys():
            labels.add(label)
    return labels

def normalize_dict_key(dict_obj, old_keys, new_keys, remove_keys):
    old_keys = list(old_keys)
    new_keys = list(new_keys)
    remove_keys = list(remove_keys)
    assert len(old_keys) == len(new_keys)
    result_dict = deepcopy(dict_obj)

    for i in range(len(old_keys)):
        if old_keys[i] in result_dict.keys():
            result_dict[new_keys[i]] = result_dict.pop(old_keys[i])
    for key in remove_keys:
        if key in result_dict.keys():
            result_dict.pop(key)
    return result_dict

old_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chổ để xe hơi', 'Hướng', 'Loại tin', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ :', 'Số toilet :', 'Tầng :']
new_keys = ['Chiều dài', 'Chiều ngang', 'Chính chủ', 'Chỗ để xe hơi', 'Hướng', 'remove', 'Lộ giới', 'Nhà bếp', 'Pháp lý', 'Phòng ăn', 'Sân thượng', 'Số lầu', 'Số phòng ngủ', 'Số phòng ngủ', 'Số toilet', 'Tầng']
remove_keys = ['remove']

def get_all_extra_infos_values(data, labels):
    extra_info_values = {}
    for label in labels:
        extra_info_values[label] = set()
    
    for item in data:
        for label in item['extra_infos'].keys():
            if item['extra_infos'][label]:
                extra_info_values[label].add(item['extra_infos'][label])
    
    return extra_info_values

def null_keys_remove_from_dict(dict_obj):
    result_dict = deepcopy(dict_obj)
    list_of_none_key = []
    for key in result_dict:
        if not result_dict[key]:
            list_of_none_key.append(key)
    for key in list_of_none_key:
        result_dict.pop(key)
    return result_dict

def normalize_text_field_in_dict(dict_obj):
    result_dict = deepcopy(dict_obj)
    for key in result_dict.keys():
        if isinstance(result_dict[key], str):
            result_dict[key] = result_dict[key].replace(',', '.')
            new_val = ''
            for c in result_dict[key]:
                if c.isalpha() or c.isnumeric() or c == '.' or c == ' ':
                    new_val += c
            result_dict[key] = new_val
    return result_dict