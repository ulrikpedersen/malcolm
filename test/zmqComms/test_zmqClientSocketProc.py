#!/bin/env dls-python
from pkg_resources import require
from collections import OrderedDict
require("mock")
require("pyzmq")
import unittest
import sys
import os
import weakref
import cothread

import logging
#logging.basicConfig()
logging.basicConfig(level=logging.DEBUG)
from mock import patch, MagicMock
# Module import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from malcolm.zmqComms.zmqClientSocket import ZmqClientSocket
from malcolm.zmqComms.zmqServerSocket import ZmqServerSocket
from malcolm.core.serialize import SType
from malcolm.core.socketInterface import ClientSocket, ServerSocket


class ZmqClientSocketProcTest(unittest.TestCase):

    def setUp(self):
        self.cs = ClientSocket.make_socket("zmq://ipc://tmp/frfes.ipc")
        self.cs.loop_run()
        self.ss = ServerSocket.make_socket("zmq://ipc:///tmp/frfess.ipc", None)
        self.ss.open(self.ss.address)

    def test_gc(self):
        cothread.Yield()

    def test_request(self):
        response = MagicMock()
        typ = SType.Call
        kwargs = OrderedDict()
        kwargs.update(endpoint="zebra1.run")
        self.cs.request(response, typ, kwargs)
        ss_msg = self.ss.recv()
        self.assertEqual(ss_msg[1], '{"type": "Call", "id": 0, "endpoint": "zebra1.run"}')
        self.assertEqual(response.call_count, 0)

    def test_response(self):
        response = MagicMock()
        self.cs.request(response, SType.Call, dict(endpoint="zebra1.run"))
        ss_msg = self.ss.recv()
        self.ss.send([ss_msg[0], '{"type": "Return", "id": 0, "value": 32}'])
        cothread.Sleep(0.1)
        response.assert_called_once_with(SType.Return, value=32)

    def tearDown(self):
        msgs = []

        def log_debug(msg):
            msgs.append(msg)

        self.cs.log_debug = log_debug
        self.cs = None
        self.ss = None
        cothread.Sleep(0.1)
        self.assertEqual(msgs, ['Garbage collecting loop', 'Stopping loop',
                                'Waiting for loop to finish', 'Loop finished',
                                'Loop garbage collected'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
