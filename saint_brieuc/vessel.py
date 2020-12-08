# ----------------------------------------------------------------------------!
import simpy
import numpy as np
import scipy.stats as st
from log import EventLog
from sites import Site
from activities import Navigate, LoadComponent, InstallComponent
from offshore import OffshoreEnvironment as OE


# ----------------------------------------------------------------------------!
class Vessel(object):
    instances = []

    def __init__(self, env: simpy.Environment, ID: str, log: EventLog,
                 port: Site, owf: Site, oe: OE, offshore_env: bool, capacity=5,
                 **kwargs):
        self.env = env
        self.log = log
        self.ID = ID
        self.port = port
        self.container = simpy.Container(env=env, capacity=capacity, init=0)
        self.owf = owf
        self.oe = oe
        self.offshore_env = offshore_env

        # Manually adjust these!
        self.sail_to_length = lognorm(mean=24 * 3600, std=1200)
        self.sail_length = lognorm(mean=3600 * 1.9, std=1800)
        self.sail_between_length = lognorm(mean=3600 * 0.5, std=300)
        self.load_length = lognorm(mean=3600 * 3.7, std=600)
        self.install_length = lognorm(mean=3600 * (33.2), std=3600)
        # self.sail_to_length = lognorm(mean=24 * 3600, std=1)
        # self.sail_length = lognorm(mean=3600 * 1.9, std=1)
        # self.sail_between_length = lognorm(mean=3600 * 0.5, std=1)
        # self.load_length = lognorm(mean=3600 * 3.7, std=1)
        # self.install_length = lognorm(mean=3600 * (33.2), std=1)

        # Add new class object to the list of instances
        Vessel.instances.append(self)

    def execute_actions(self):
        env = self.env

        # Navigate from offshore to port
        sail = Navigate(duration=self.sail_to_length.rvs(),
                        description='Navigate from offshore to site',
                        **self.__dict__)
        yield env.process(sail.execute())

        while True:
            # Check whether it is necessary to perform activities
            if self.port.container.level == 0:
                break

            # Request for a berth before loading
            with self.port.resources.request() as req:

                self.log.entry(description='Request for a berth',
                               activity_state='Requested', **self.__dict__)
                yield req
                self.log.entry(description='Request for a berth',
                               activity_state='Granted', **self.__dict__)

                # Load components onto vessel's deck
                while self.container.level < self.container.capacity:
                    load = LoadComponent(duration=self.load_length.rvs(),
                                         **self.__dict__)
                    yield env.process(load.execute())

                    if self.port.container.level == 0:
                        break

            # Navigate from port to site
            sail = Navigate(duration=self.sail_length.rvs(),
                            description='Navigate from port to site',
                            **self.__dict__)
            yield env.process(sail.execute())

            # Install component
            install = InstallComponent(duration=self.install_length.rvs(),
                                       **self.__dict__)
            yield env.process(install.execute())

            # Sail to the next site if components still on deck
            while self.container.level > 0:

                sail = Navigate(duration=self.sail_between_length.rvs(),
                                description='Navigate to the next site',
                                **self.__dict__)
                yield env.process(sail.execute())

                install = InstallComponent(duration=self.install_length.rvs(),
                                           **self.__dict__)
                yield env.process(install.execute())

            # Navigate from site to port
            sail = Navigate(duration=self.sail_length.rvs(),
                            description='Navigate from site to port',
                            **self.__dict__)
            yield env.process(sail.execute())


# ----------------------------------------------------------------------------!
def lognorm(mean, std):
    mu = np.log(mean ** 2 / np.sqrt(mean ** 2 + std ** 2))
    sigma = np.sqrt(np.log(1 + std ** 2 / mean ** 2))
    return st.lognorm(s=sigma, scale=np.exp(mu))
