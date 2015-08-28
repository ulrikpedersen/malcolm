from malcolm.zmqComms.zmqSerialize import deserialize, serialize_ready, \
    serialize_error, serialize_return, SType
import zmq
from zmqProcess import ZmqProcess
import logging
from malcolm.zmqComms.zmqSerialize import serialize_value
log = logging.getLogger(__name__)


class ZmqDeviceWrapper(ZmqProcess):

    def __init__(self, name, device_class, be_addr="ipc://frbe.ipc",
                 timeout=None, **device_kwargs):
        super(ZmqDeviceWrapper, self).__init__(timeout)
        self.name = name
        self.be_addr = be_addr
        self.be_stream = None
        self.device_class = device_class
        self.device_kwargs = device_kwargs
        # id->callback function
        self.subscriptions = {}

    def setup(self):
        """Sets up PyZMQ and creates all streams."""
        super(ZmqDeviceWrapper, self).setup()

        # Make the device object and run it
        self.device = self.device_class(self.name, **self.device_kwargs)
        self.device.start_event_loop()

        # Create the frontend stream and add the message handler
        self.be_stream = self.stream(zmq.DEALER, self.be_addr, bind=False)
        self.be_stream.on_recv(self.handle_be)

        # Say hello
        log.info(
            "{}: Sending ready message to {}".format(self.name, self.be_addr))
        self.be_send("", serialize_ready(self.name))

    def be_send(self, clientid, data):
        log.debug("be_send {}".format((clientid, data)))
        self.be_stream.send_multipart([clientid, data])

    def do_func(self, clientid, f, _id, args):
        log.debug("do_func {} {}".format(f, args))

        def send_status(status, changes):
            if changes != ["timeStamp"]:
                self.be_send(clientid, serialize_value(_id, status))

        self.device.add_listener(send_status, prefix="status", changes=True)
        try:
            ret = f(**args)
        except Exception as e:
            log.exception(
                "{}: threw exception calling {}".format(self.name, f))
            self.be_send(clientid, serialize_error(_id, e))
        else:
            self.be_send(clientid, serialize_return(_id, ret))
        self.device.remove_listener(send_status)

    def do_call(self, clientid, d):
        # check that we have the right type of message
        device, method = d["method"].split(".", 1)
        assert device == self.name, "Wrong device name {}".format(device)
        assert "id" in d, "No id in {}".format(d)
        if method == "exit":
            # Just exit now
            self.be_send(clientid, serialize_return(d["id"], self.exit()))
        else:
            # Call a device method
            assert method in self.device.methods, \
                "Invalid function {}".format(method)
            args = d.get("args", {})
            f = self.device.methods[method]
            # Run the function
            import cothread
            cothread.Spawn(self.do_func, clientid, f, d["id"], args)

    def prepare_parameters(self, d):
        # check that we have the right type of message
        param = d["param"]
        if "." in param:
            device, param = param.split(".", 1)
        else:
            device, param = param, None
        assert device == self.name, "Wrong device name {}".format(device)
        assert "id" in d, "No id in {}".format(d)
        parameters = self.device
        if param is not None:
            for p in param.split("."):
                try:
                    parameters = parameters[p]
                except:
                    parameters = parameters.to_dict()[p]
        return parameters

    def do_get(self, clientid, d):
        parameters = self.prepare_parameters(d)
        self.be_send(clientid, serialize_return(d["id"], parameters))

    def do_subscribe(self, clientid, d):
        assert d["id"] not in self.subscriptions, \
            "Subscription already exists for id {}".format(d["id"])
        parameters = self.prepare_parameters(d)
        self.be_send(clientid, serialize_value(d["id"], parameters))

        def subscription(value, changes=None):
            self.be_send(clientid, serialize_value(d["id"], value, changes))

        self.device.add_listener(subscription, d["param"].split(".", 1)[-1])
        self.subscriptions[d["id"]] = subscription

    def do_unsubscribe(self, clientid, d):
        assert d["id"] in self.subscriptions, \
            "Subscription doesn't exist for id {}".format(d["id"])
        self.device.remove_listener(self.subscriptions.pop(d["id"]))
        self.be_send(clientid, serialize_return(d["id"], None))

    def handle_be(self, msg):
        log.debug("handle_be {}".format(msg))
        clientid, data = msg
        # Classify what type of method it is
        try:
            d = deserialize(data)
            assert "id" in d, "No id in {}".format(d)
        except Exception as e:
            self.be_send(clientid, serialize_error(-1, e))
            return
        # Now do the identified action
        try:
            func = {
                SType.Call: self.do_call,
                SType.Get: self.do_get,
                SType.Subscribe: self.do_subscribe,
                SType.Unsubscribe: self.do_unsubscribe,
            }[d["type"]]
            func(clientid, d)
        except Exception as e:
            log.exception(
                "{}: threw exception handling {}".format(self.name, d))
            # send error up the chain
            self.be_send(clientid, serialize_error(d["id"], e))

    def exit(self):
        self.device.exit()
        super(ZmqDeviceWrapper, self).exit()