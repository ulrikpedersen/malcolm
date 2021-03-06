import abc

from enum import Enum

from .method import wrap_method
from .base import weak_method
from .device import Device
from .stateMachine import StateMachine
from .attribute import Attribute


class DState(Enum):
    # These are the states that our machine supports
    Fault, Idle, Configuring, Ready, Running, Pausing, Paused, Aborting,\
        Aborted, Resetting = range(10)

    @classmethod
    def rest(cls):
        return [cls.Fault, cls.Idle, cls.Ready, cls.Aborted]

    @classmethod
    def pausedone(cls):
        return [cls.Fault, cls.Aborted, cls.Paused]

    @classmethod
    def abortable(cls):
        return [cls.Configuring, cls.Ready, cls.Running, cls.Pausing,
                cls.Paused, cls.Resetting]

    @classmethod
    def configurable(cls):
        return [cls.Idle, cls.Ready]

    @classmethod
    def runnable(cls):
        return [cls.Ready, cls.Paused]

    @classmethod
    def resettable(cls):
        return [cls.Fault, cls.Aborted]

    def to_dict(self):
        choices = [e.name for e in self.__class__]
        d = dict(index=self.value, choices=choices)
        return d


class DEvent(Enum):
    # These are the messages that we will respond to
    Error, Reset, ResetSta, Config, ConfigSta, Run, RunSta, Abort, AbortSta, \
        Pause, PauseSta = range(11)


class RunnableDevice(Device):

    def __init__(self, name, timeout=None):
        # superclass init
        super(RunnableDevice, self).__init__(name, timeout=timeout)

        # Make a statemachine
        sm = StateMachine(name + ".stateMachine", DState.Idle, DState.Fault)
        self.add_stateMachine(sm)

        # some shortcuts for the state table
        do, t, s, e = self.shortcuts()

        # Error condition generated by device
        t(s,             e.Error,     do.error,     s.Fault)
        # Normal operations
        t(s.resettable(), e.Reset,    do.reset,     s.Resetting)
        t(s.Resetting,   e.ResetSta,  do.resetsta,  s.Resetting, s.Idle)
        t(s.Idle,        e.Config,    do.config,    s.Configuring)
        t(s.Configuring, e.ConfigSta, do.configsta, s.Configuring, s.Ready)
        t(s.Ready,       e.Config,    do.config,    s.Configuring)
        t(s.Ready,       e.Run,       do.run,       s.Running)
        t(s.Running,     e.RunSta,    do.runsta,    s.Running, s.Idle, s.Ready)
        # Abort
        t(s.abortable(), e.Abort,     do.abort,     s.Aborting)
        t(s.Aborting,    e.AbortSta,  do.abortsta,  s.Aborting, s.Aborted)

        # Timeout for functions
        self.add_attributes(
            timeout=Attribute(float, "Time in seconds to wait for function"))

        # Override the error handler of the stateMachine
        sm.do_error = weak_method(self.do_error)

    def shortcuts(self):
        # Shortcut to all the self.do_ functions
        class do:
            pass
        for fname in dir(self):
            if fname.startswith("do_"):
                setattr(do, fname[3:], getattr(self, fname))

        # Shortcut to transition function, state list and event list
        t = self.stateMachine.transition
        s = DState
        e = DEvent
        return (do, t, s, e)

    def do_error(self, error):
        """Handle an error"""
        return DState.Fault, str(error)

    @abc.abstractmethod
    def do_reset(self):
        """Check and attempt to clear any error state, arranging for a
        callback doing self.post(DEvent.ResetSta, resetsta) when progress has
        been made, where resetsta is any device specific reset status
        """

    @abc.abstractmethod
    def do_resetsta(self, resetsta):
        """Examine configsta for configuration progress, returning
        DState.Resetting if still in progress, or DState.Idle if done.
        """

    @abc.abstractmethod
    def do_config(self, **config_params):
        """Start doing a configuration using config_params, arranging for a
        callback doing self.post(DEvent.ConfigSta, configsta) when progress has
        been made, where configsta is any device specific configuration status
        """

    @abc.abstractmethod
    def do_configsta(self, configsta):
        """Examine configsta for configuration progress, returning
        DState.Configuring if still in progress, or DState.Ready if done.
        """

    @abc.abstractmethod
    def do_run(self):
        """Start doing a run, arranging for a callback doing
        self.post(DEvent.RunSta, runsta) when progress has been made, where
        runsta is any device specific run status
        """

    @abc.abstractmethod
    def do_runsta(self, runsta):
        """Examine runsta for run progress, returning DState.Running if still
        in progress, DState.Ready if done and another run can be started
        without reconfiguration, or DState.Idle if done and configuration is
        needed before another run can be started.
        """

    @abc.abstractmethod
    def do_abort(self):
        """Start doing an abort, arranging for a callback doing
        self.post(DEvent.AbortSta, runsta) when progress has been made, where
        abortsta is any device specific abort status
        """

    @abc.abstractmethod
    def do_abortsta(self, abortsta):
        """Examine abortsta for abort progress, returning DState.Aborting if still
        in progress or DState.Aborted if done.
        """

    @abc.abstractmethod
    def assert_valid(self, arg1, arg2="arg2default"):
        """Check whether a set of configuration parameters is valid or not. Each
        parameter name must match one of the names in self.attributes. This set
        of parameters should be checked in isolation, no device state should be
        taken into account. It is allowed from any DState and raises an error
        if the set of configuration parameters is invalid.
        """

    @wrap_method(only_in=DState.abortable())
    def abort(self, timeout=None):
        """Abort configuration or abandon the current run whether it is
        running or paused. It blocks until the device is in a rest state:
         * Normally it will return a DState.Aborted Status
         * If something goes wrong it will return a DState.Fault Status
        """
        timeout = timeout or self.timeout
        self.stateMachine.post(DEvent.Abort)
        self.wait_until(DState.rest(), timeout=timeout)

    @wrap_method(only_in=DState.resettable())
    def reset(self, timeout=None):
        """Try and reset the device into DState.Idle. It blocks until the
        device is in a rest state:
         * Normally it will return a DState.Idle Status
         * If something goes wrong it will return a DState.Fault Status
        """
        timeout = timeout or self.timeout
        self.stateMachine.post(DEvent.Reset)
        self.wait_until(DState.rest(), timeout=timeout)

    @wrap_method(only_in=DState.configurable(), args_from=assert_valid)
    def configure(self, timeout=None, **params):
        """Assert params are valid, then use them to configure a device for a run.
        It blocks until the device is in a rest state:
         * Normally it will return a DState.Configured Status
         * If the user aborts then it will return a DState.Aborted Status
         * If something goes wrong it will return a DState.Fault Status
        """
        timeout = timeout or self.timeout
        self.assert_valid(**params)
        self.stateMachine.post(DEvent.Config, **params)
        self.wait_until(DState.rest(), timeout=timeout)

    @wrap_method(only_in=DState.runnable())
    def run(self, timeout=None):
        """Start a configured device running. It blocks until the device is in a
        rest state:
         * Normally it will return a DState.Idle Status
         * If the device allows many runs from a single configure the it
           will return a DState.Ready Status
         * If the user aborts then it will return a DState.Aborted Status
         * If something goes wrong it will return a DState.Fault Status
        """
        timeout = timeout or self.timeout
        self.stateMachine.post(DEvent.Run)
        self.wait_until(DState.rest(), timeout=timeout)

    @wrap_method(only_in=DState, args_from=assert_valid)
    def configure_run(self, timeout=None, **params):
        """Try and configure and run a device in one step. It blocks until the
        device is in a rest state:
         * Normally it will return a DState.Idle Status
         * If the device allows many runs from a single configure then it
           will return a DState.Ready Status
         * If the user aborts then it will return a DState.Aborted Status
         * If something goes wrong it will return a DState.Fault Status
        """
        timeout = timeout or self.timeout
        # If we can't configure from our current state
        if self.state not in DState.configurable():
            # If we are abortable then abort
            if self.state in DState.abortable():
                self.abort(timeout=timeout)
            # Now try a reset to bring us back to idle
            if self.state in DState.resettable():
                self.reset(timeout=timeout)
        # Now if we are configurable then do so
        if self.state in DState.configurable():
            self.configure(timeout=timeout, **params)
            # And now if we are ready then do a run
            if self.state == DState.Ready:
                self.run(timeout=timeout)
