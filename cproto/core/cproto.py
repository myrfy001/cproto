from __future__ import absolute_import

import json
import base64
import threading
from os import path
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from websocket import create_connection, WebSocket

from cproto.domains.factory import DomainFactory


ROOT_DIR = path.abspath(path.dirname(path.dirname(__file__)))


class WS(WebSocket):
    def connect(self, *args, **kwargs):
        super(self.__class__, self).connect(*args, **kwargs)

        self.read_lock = threading.Condition()
        read_thread = threading.Thread(target=self.read_stream)
        read_thread.setDaemon(True)
        read_thread.start()

    def atomic_send(self, *args, **kwargs):
        with self.read_lock:
            self.send(*args)
            data = self.recv()
            self.read_lock.notify()

        return data

    def read_stream(self):
        while self.connected:
            with self.read_lock:
                self.read_lock.wait()
                self.recv()


class CProto(object):

    def __init__(self, host='127.0.0.1', port=9222):
        res = urlopen('http://{0}:{1}/json'.format(host, port))

        url = json.loads(res.read())[0]['webSocketDebuggerUrl']
        self.ws = WS()
        self.ws.connect(url)

        with open(path.join(ROOT_DIR, 'resources/protocol.json'), 'rb') as f:
            data = json.loads(f.read())

        for d in data['domains']:
            domain_name = d['domain']

            # Build Domain Class from protocol
            DomainClass = DomainFactory(domain_name, d['commands'])

            # Set WebSocket attribute
            setattr(DomainClass, 'ws', self.ws)

            # Set Domain's Class as a property
            setattr(self, domain_name, DomainClass)

    def close(self):
        self.ws.close()
