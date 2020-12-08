# ----------------------------------------------------------------------------!
import simpy
from log import EventLog


# ----------------------------------------------------------------------------!
class Site(object):
    def __init__(self, env: simpy.Environment, log: EventLog, ID: str,
                 resources: int = 1, capacity: int = 1, level: int = 0,
                 **kwargs):

        self.env = env
        self.log = log
        self.ID = ID
        self.resources = simpy.Resource(env=env, capacity=resources)
        self.container = simpy.Container(env=env, capacity=capacity,
                                         init=level)
