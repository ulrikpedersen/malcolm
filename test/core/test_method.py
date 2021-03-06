#!/bin/env dls-python
from pkg_resources import require
import malcolm
require("mock")
require("cothread")
import unittest
import sys
import os
from enum import Enum
import inspect
#import logging
# logging.basicConfig(level=logging.DEBUG)
from mock import patch, MagicMock
# Module import
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from malcolm.core.method import wrap_method, HasMethods
from malcolm.core.attribute import Attribute


class TState(Enum):
    State1, State2 = range(2)


class Container(HasMethods):

    def __init__(self):
        self.add_methods(
            nframes=Attribute(int, "Number of frames"),
            exposure=Attribute(float, "Detector exposure")
        )
        self.state = TState.State1

    @wrap_method(TState.State1)
    def f(self, nframes, exposure=0.1):
        "Return total time"
        return nframes * exposure

    @wrap_method(TState.State2, f)
    def g(self, **params):
        "Proxy thing"
        pass


class MethodTest(unittest.TestCase):

    def setUp(self):
        self.c = Container()

    def test_calling_f(self):
        self.assertEqual(self.c.f(3, 4), 12)

    def test_attribute_description(self):
        method = self.c.methods["f"]
        self.assertEqual(method, self.c.f)
        self.assertEqual(method.descriptor, "Return total time")
        nframes = method.args["nframes"]
        self.assertEqual(nframes.descriptor, "Number of frames")
        self.assertEqual(nframes.typ, int)
        self.assertEqual(nframes.value, None)
        self.assertEqual(nframes.tags, ("argument:required",))
        exposure = method.args["exposure"]
        self.assertEqual(exposure.descriptor, "Detector exposure")
        self.assertEqual(exposure.typ, float)
        self.assertEqual(exposure.value, 0.1)
        self.assertEqual(exposure.tags, ())
        self.assertEqual(method.valid_states, [TState.State1])

    def test_attribute_override_description(self):
        method = self.c.methods["g"]
        self.assertEqual(method, self.c.g)
        self.assertEqual(method.descriptor, "Proxy thing")
        nframes = method.args["nframes"]
        self.assertEqual(nframes.descriptor, "Number of frames")
        self.assertEqual(nframes.typ, int)
        self.assertEqual(nframes.value, None)
        self.assertEqual(nframes.tags, ("argument:required",))
        exposure = method.args["exposure"]
        self.assertEqual(exposure.descriptor, "Detector exposure")
        self.assertEqual(exposure.typ, float)
        self.assertEqual(exposure.value, 0.1)
        self.assertEqual(exposure.tags, ())
        self.assertEqual(method.valid_states, [TState.State2])

    def test_to_dict(self):
        d = self.c.f.to_dict()
        self.assertEqual(
            d.keys(), ['name', 'descriptor', 'args', 'valid_states'])
        self.assertEqual(d.values(), ['f', 'Return total time', {'exposure': self.c.f.args[
                         "exposure"], 'nframes': self.c.f.args["nframes"]}, ['State1']])

if __name__ == '__main__':
    unittest.main(verbosity=2)
