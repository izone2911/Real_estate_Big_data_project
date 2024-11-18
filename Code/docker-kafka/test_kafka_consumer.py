from confluent_kafka import Consumer
import json

def run_consumer():
    c = Consumer({'bootstrap.servers': '192.168.102.7:9192,192.168.102.7:9292,192.168.102.7:9392',
                  'group.id': '1233'})
    c.subscribe(['test'])

    consumed = []

    while True:
        msg = c.poll(1.0)

        if msg is None:
            print(len(consumed))
            continue
        if msg.error():
            print(f'Consumer error: {msg.error()}')
            continue
        
        msg_received = msg.value()
        # msg_received = msg.value()
        consumed.append(msg_received)
        print(f'Received message: {msg_received}')
    
    c.close()

if __name__ == '__main__':
    run_consumer()