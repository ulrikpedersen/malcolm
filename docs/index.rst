malcolm
=======

This whole page should make up README.rst

What is malcolm, and why might you want to use it.

Installation
------------

To install the latest release, type::

    pip install malcolm

To install the latest code directly from source, type::

    pip install git+git://github.com/dls-controls/malcolm.git

Configuration
-------------

Some basic configuration options

Usage
-----

There is a dummy detector distributed with malcolm, that allows you to change
the exposure and number of frames, and simulates an acquisition using these
parameters. You can run up a server which contains this by changing directory
to the checked out version and running::
    
    [tmc43@pc0013 malcolm]$ ./example/dummy_det_server.py 
    INFO:malcolm.zmqComms.zmqMalcolmRouter:Binding client facing socket on tcp://127.0.0.1:5600
    INFO:malcolm.zmqComms.zmqDeviceWrapper:det: Sending ready message to ipc://frbe.ipc
    INFO:malcolm.zmqComms.zmqMalcolmRouter:Binding device facing socket on ipc://frbe.ipc
    INFO:malcolm.zmqComms.zmqMalcolmRouter:Device det connected
    
It has now started a malcolm router and a device det, and is ready to receive commands.
You can now start a client to this server in an interactive client and send messages
to it::

    [tmc43@pc0013 malcolm]$ dls-python -i ./example/dummy_det_client.py
    Try running det.configure(exposure=0.2, nframes=10)
    >>> 

The client det object has now been populated with all the methods that the server det
object supports::

    >>> dir(det)
    ['__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_fc', 'abort', 'assert_valid', 'configure', 'configure_run', 'do_call', 'pause', 'reset', 'resume', 'retrace', 'run', 'state', 'status']
    >>> 
    
You can then run a method which will print the status updates as it runs::

    >>> det.configure(exposure=0.2, nframes=10)
    Configuring: Configuring started
    Ready: Configuring finished
    >>> 

If you Ctrl-C in the middle of a long running function then it will send an abort
and return when it is aborted::

    >>> det.run()
    Running: Starting run
    Running: Running in progress 0% done
    Running: Running in progress 10% done
    Running: Running in progress 20% done
    Running: Running in progress 30% done
    ^CAborting: Aborting
    Aborting: Waiting for detector to stop
    Aborted: Aborted
    >>> 

You can also open another client which will share the same state as the first::

    [tmc43@pc0013 malcolm]$ dls-python -i ./example/dummy_det_client.py
    Try running det.configure(exposure=0.2, nframes=10)
    >>> det.state
    'Aborted'
    >>> det.reset()
    Resetting: Resetting
    Idle: Reset complete
    >>> det.configure(exposure=0.2, nframes=10)
    Configuring: Configuring started
    Ready: Configuring finished
    >>> 

If we use this second client to start a run, then pause, retrace and resume it from
the first, we get this output on the second client::

    >>> det.run()
    Running: Starting run
    Running: Running in progress 0% done
    Running: Running in progress 10% done
    Running: Running in progress 20% done
    Running: Running in progress 30% done
    Running: Running in progress 40% done
    Running: Running in progress 50% done
    Pausing: Pausing started
    Pausing: Waiting for detector to stop
    Pausing: Reconfiguring detector for 5 frames
    Paused: Pausing finished
    Pausing: Retracing started
    Pausing: Reconfiguring detector for 7 frames
    Paused: Pausing finished
    Running: Starting run
    Running: Running in progress 30% done
    Running: Running in progress 40% done
    Running: Running in progress 50% done
    Running: Running in progress 60% done
    Running: Running in progress 70% done
    Running: Running in progress 80% done
    Running: Running in progress 90% done
    Idle: Running in progress 100% done
    >>> 

And this on the first::

    >>> det.pause()
    Pausing: Pausing started
    Pausing: Waiting for detector to stop
    Pausing: Reconfiguring detector for 5 frames
    Paused: Pausing finished
    >>> det.retrace(steps=2)
    Pausing: Retracing started
    Pausing: Reconfiguring detector for 7 frames
    Paused: Pausing finished
    >>> det.resume()
    Running: Starting run
    >>> 

That's it! To get a more in depth view of the architecture, please read on to the next chapter.

