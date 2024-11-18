import os
import json
import logging

from hdfs import InsecureClient
from confluent_kafka import Consumer

logging.basicConfig(
    handlers=[
        logging.FileHandler('./hadoop-consumer-log', mode='a'),
        logging.StreamHandler()
    ],
    format='%(asctime)s, %(name)s %(levelname)s %(message)s',
    datefmt='(%Y-%m-%d %H:%M:%S)',
    level=logging.INFO,
    force=True,
)

NAMENODE_URL = os.environ.get('NAMENODE_URL')
HDFS_USER = os.environ.get('HDFS_USER')
BOOSTRAP_SERVERS = os.environ.get('BOOSTRAP_SERVERS')
CONSUMER_GROUP_ID = os.environ.get('CONSUMER_GROUP_ID')
SUBSCRIBE_LIST = os.environ.get('SUBSCRIBE_LIST').split(',')
POLL_TIMEOUT = float(os.environ.get('POLL_TIMEOUT'))

hdfs_client = InsecureClient(url=NAMENODE_URL, user=HDFS_USER)

def check_hdfs_path_existence(path):
    path_existence = hdfs_client.status(path, strict=False)
    if path_existence:
        return True
    else:
        return False

def get_consumer(bootsrap_servers, group_id, subscribe_list):
    c = Consumer({
        'bootstrap.servers': bootsrap_servers,
        'group.id': group_id
    })
    c.subscribe(subscribe_list)
    return c

def push_to_hdfs(hdfs_file_path, msg):
    if not check_hdfs_path_existence(hdfs_file_path):
        append = False
        logging.info(f'Create file: {hdfs_file_path}')
    else:
        append = True
    with hdfs_client.write(hdfs_file_path, encoding='utf8', append=append) as writer:
        writer.write(f'{msg}\n')


if __name__ == '__main__':
    consumer = get_consumer(BOOSTRAP_SERVERS, CONSUMER_GROUP_ID, SUBSCRIBE_LIST)

    count = 0
    while True:
        msg = consumer.poll(POLL_TIMEOUT)

        if msg is None:
            continue
        if msg.error():
            logging.info(f'Consumer error: {msg.error()}.')
            continue

        msg_value = json.loads(msg.value().decode('utf-8'))
        hdfs_file_path = f'/{HDFS_USER}/real_estate_data/{msg.topic()}.jsonl'
        push_to_hdfs(hdfs_file_path, msg_value)
        count += 1
        logging.info(f'Consumed message {count} in topic {msg.topic()}, partition {msg.partition()} at offset {msg.offset()}')

    consumer.close()

    
