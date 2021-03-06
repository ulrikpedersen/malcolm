from collections import OrderedDict

from .base import Base


class HasListeners(Base):

    def add_listener(self, callback, prefix=""):
        """Add a listener callback function to be called when something
        changes.
        It should have call signature:
          def callback(changes)
        Where changes is a dict of prefix->new value
        """
        # Lazily make listeners dict
        if not hasattr(self, "_listeners"):
            self._listeners = OrderedDict()
        assert callback not in self._listeners, \
            "Callback function {} already in callback list".format(
                callback)
        self._listeners[callback] = prefix

    def remove_listener(self, callback):
        """Remove listener callback function"""
        self.log_debug("Removing listener {}".format(callback))
        self._listeners.pop(callback)

    def get_endpoint(self, ename):
        endpoint = self
        if ename:
            for e in ename.split("."):
                if hasattr(endpoint, "to_dict"):
                    endpoint = endpoint.to_dict()
                assert e in endpoint, "{} not in {}".format(e, endpoint.keys())
                endpoint = endpoint[e]
        return endpoint

    def notify_listeners(self, changes, prefix=""):
        if not hasattr(self, "_listeners"):
            return
        # Add on prefix to changes
        changes = {prefix + k: v for k, v in changes.items()}
        self.log_debug("Notifying listeners of {}".format(changes))
        for callback, prefix in self._listeners.items():
            filt_changes = {}
            for cname, cvalue in changes.items():
                if cname.startswith(prefix):
                    filt_changes[cname[len(prefix):].lstrip(".")] = cvalue
            # If we have a dict with a single entry "", we are monitoring
            # a single item, not a structure, so make it "."
            if filt_changes:
                if filt_changes.keys() == [""]:
                    filt_changes["."] = filt_changes.pop("")
                cname = getattr(callback, "__name__", "callback")
                value = self.get_endpoint(prefix)
                self.log_debug("Calling {}({}, {})"
                               .format(cname, value, filt_changes))
                try:
                    callback(value, filt_changes)
                except:
                    self.log_exception("{}({}) raised exception"
                                       .format(callback.__name__, filt_changes))
