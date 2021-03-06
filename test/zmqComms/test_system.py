#!/bin/env dls-python
from pkg_resources import require
from malcolm.core.device import Device
from malcolm.core.method import wrap_method
from malcolm.core.loop import TimerLoop
from malcolm.core.process import Process
from malcolm.core.directoryService import DirectoryService
require("mock")
require("pyzmq")
import unittest
import sys
import os
import json
import zmq
import time

import logging
logging.basicConfig(level=logging.DEBUG)
# format="%(asctime)s;%(levelname)s;%(message)s")
# Module import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class Counter(Device):
    def __init__(self, name, timeout=None):
        super(Counter, self).__init__(name, timeout)
        self.counter = 0
        self.add_loop(TimerLoop("timer", self.do_count, 0.01))

    def do_count(self):
        self.counter += 1

    @wrap_method()
    def get_count(self):
        return self.counter

    @wrap_method()
    def hello(self):
        self.cothread.Sleep(0.1)
        return "world"

    @wrap_method()
    def long_hello(self):
        self.cothread.Sleep(0.5)
        return "long world"

    def exit(self):
        pass

class ZmqSystemTest(unittest.TestCase):

    def setUp(self):
        """
        Creates and starts a PongProc process and sets up sockets to
        communicate with it.

        """
        self.ds = DirectoryService(["zmq://ipc:///tmp/frfe.ipc"])
        self.ds.create_Counter("The Counter")
        self.ds.start()
        self.lp = Process([], "Local Process", ds_string="zmq://ipc:///tmp/frfe.ipc")
        self.lp.run(block=False)
        self.c = self.lp.get_device("The Counter")

    def test_simple_function(self):
        import cothread
        cothread.Sleep(0.2)
        start = self.c.get_count()
        self.assertEqual(self.c.hello(), "world")
        # Hello world takes about 10 ticks
        self.assertAlmostEqual(self.c.get_count(), start + 10, delta=3)
        # Do a long running call
        s = cothread.Spawn(self.c.long_hello)
        # Check it returns immediately
        self.assertAlmostEqual(self.c.get_count(), start + 10, delta=3)
        self.assertEqual(self.c.hello(), "world")
        # Hello world takes 10 ticks
        self.assertAlmostEqual(self.c.get_count(), start + 20, delta=3)
        self.assertEqual(s.Wait(), "long world")
        # Long hello takes about 50 ticks from send
        self.assertAlmostEqual(self.c.get_count(), start + 60, delta=3)

    def tearDown(self):
        """
        Sends a kill message to the pp and waits for the process to terminate.

        """
        # Send a stop message to the prong process and wait until it joins
        print self.lp.ds.ping()
        self.lp.ds.exit()
        self.lp.exit()
        self.ds.join()

if __name__ == '__main__':
    unittest.main(verbosity=2)
