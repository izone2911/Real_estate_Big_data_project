from confluent_kafka import Producer
import json
import time
import ast

def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def run_producer():
    p = Producer({'bootstrap.servers': '20.239.82.205:9192,20.239.82.205:9292,20.239.82.205:9392'})
    with open('./test_data.json') as f:
        data = json.load(f)
    for item in data:
        p.produce('test', json.dumps(item, ensure_ascii=False), callback=delivery_report)
        # p.produce('bds', item, callback=delivery_report)
        # time.sleep(1)
    p.flush()

if __name__ == '__main__':
    run_producer()