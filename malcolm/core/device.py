import inspect
from collections import OrderedDict

from .attribute import HasAttributes
from .stateMachine import HasStateMachine
from .method import HasMethods, wrap_method
from .loop import HasLoops
from .serialize import Serializable


def not_process_creatable(cls):
    cls.not_process_creatable.append(cls)
    return cls


@not_process_creatable
class Device(HasAttributes, HasMethods, HasStateMachine, HasLoops,
             Serializable):
    _endpoints = "name,descriptor,tags,methods,stateMachine,attributes".split(
        ",")
    not_process_creatable = []

    def __init__(self, name, timeout=None):
        super(Device, self).__init__(name)
        self.timeout = timeout

    def loop_run(self):
        self.add_methods()
        super(Device, self).loop_run()

    def create_device(self, cls, name, *args, **kwargs):
        """Locally available method to create device, will be overridden if
        running under a process"""
        return cls(name, *args, **kwargs)

    def get_device(self, device):
        """If running under a process, this will allow devices to be connected to
        from the local process or DirectoryService"""
        raise AssertionError("Device not running under Process")

    @classmethod
    def subclasses(cls):
        """Return list of subclasses non-abstract subclasses"""
        subclasses = OrderedDict([(cls.__name__, cls)])
        for s in cls.__subclasses__():
            for g in s.subclasses():
                if g.__name__ not in subclasses:
                    subclasses[g.__name__] = g
        return subclasses.values()

    @classmethod
    def baseclasses(cls):
        return [x for x in inspect.getmro(cls) if issubclass(x, Device)]

    @wrap_method()
    def exit(self):
        """Stop the event loop and destoy the device"""
        self.__del__()

    @wrap_method()
    def ping(self):
        """Just return 'pong'. Used for heartbeat"""
        return "pong"

    def to_dict(self):
        """Serialize this object"""
        baseclasses = [x.__name__ for x in self.baseclasses()]
        return super(Device, self).to_dict(
            tags=baseclasses,
            descriptor=self.__doc__,
            attributes=getattr(self, "attributes", None),
            methods=getattr(self, "methods", None),
            stateMachine=getattr(self, "stateMachine", None))
