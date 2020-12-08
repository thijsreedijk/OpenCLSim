# ----------------------------------------------------------------------------!
import simpy
from sites import Site
from log import EventLog
from offshore import OffshoreEnvironment as OE


# ----------------------------------------------------------------------------!
class Navigate(object):
    def __init__(self, env: simpy.Environment, log: EventLog, ID: str,
                 port: Site, container: simpy.Container, owf: Site, oe: OE,
                 duration: float, description='Navigate', **kwargs):

        self.env = env
        self.log = log
        self.ID = ID
        self.description = description
        self.port = port
        self.container = container
        self.owf = owf
        self.oe = oe
        self.limit = 10  # <= When wave height greater than 10[m] no work!
        self.duration = duration

    def execute(self):
        self.log.entry(activity_state='Initiated', **self.__dict__)

        if self.oe is not None:
            if self.oe.met.Hs.max() > self.limit:
                yield self.env.process(self.oe.request_window(**self.__dict__))

        yield self.env.timeout(self.duration)
        self.log.entry(activity_state='Completed', **self.__dict__)


# ----------------------------------------------------------------------------!
class LoadComponent(object):
    def __init__(self, env: simpy.Environment, log: EventLog, ID: str,
                 port: Site, container: simpy.Container, owf: Site,
                 duration: float, description='Load components', **kwargs):

        self.env = env
        self.log = log
        self.ID = ID
        self.duration = duration
        self.description = description
        self.port = port
        self.container = container
        self.owf = owf

    def execute(self):

        self.log.entry(activity_state='Initiated', **self.__dict__)
        yield self.env.timeout(self.duration)

        yield self.port.container.get(1)
        yield self.container.put(1)

        self.log.entry(activity_state='Completed', **self.__dict__)


# ----------------------------------------------------------------------------!
class InstallComponent(object):
    def __init__(self, env: simpy.Environment, log: EventLog, ID: str,
                 port: Site, container: simpy.Container, owf: Site, oe: OE,
                 offshore_env: bool, duration: float,
                 description='Install component', **kwargs):

        self.env = env
        self.log = log
        self.ID = ID
        self.duration = duration
        self.description = description
        self.port = port
        self.container = container
        self.owf = owf
        self.oe = oe
        self.limit = 1.5
        self.offshore_env = offshore_env

    def execute(self):
        self.log.entry(activity_state='Initiated', **self.__dict__)

        if self.offshore_env:
            if (self.oe.met.Hs.max() > self.limit):
                yield self.env.process(self.oe.request_window(**self.__dict__))

        yield self.env.timeout(self.duration)
        yield self.container.get(1)
        yield self.owf.container.put(1)
        self.log.entry(activity_state='Completed', **self.__dict__)
