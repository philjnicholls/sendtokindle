import os

import redis
from rq import Worker, Queue, Connection

listen = ['default']

redis_host = os.getenv('REDIS_HOST', 'localhost:6379')

conn = redis.from_url(f'redis://{redis_host}')

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
