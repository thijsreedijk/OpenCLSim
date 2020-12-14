''' CONTAINS CLASSES FOR GENERATING ENTITIES. '''
# ----------------------------------------------------------------------------!
import simpy
import numpy as np
from .log import (EventLog, ActivityState)
from .sites import Site
from .activities import (Cruise, LoadComponent, InstallComponent,
                         RequestWeatherWindow)
from .appendix import lognorm
from .offshore import OffshoreEnvironment


# ----------------------------------------------------------------------------!
class InstallationVessel(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object for generating a general installation vessel
        that is used for installation of OWF components. The class
        contains vessel characteristics as well as the activities
        carried out by an installation vessel.
    -------------------------------------------------------------------
    Parameters:
        env: simpy.Environment
    -------------------------------------------------------------------
    '''

    instances = []

    def __init__(self, ID: str, env: simpy.Environment, log: EventLog,
                 oe: OffshoreEnvironment, owf: Site, port: Site, capacity: int,
                 level: int, resources: int, **kwargs):

        # Assign arguments to class attributes.
        self.__dict__ = locals()
        self.__dict__['equipment'] = self.__dict__.pop('self')

        # Initialise deck container using the SimPy container.
        self.container = simpy.Container(env=self.env, capacity=capacity,
                                         init=level)

        # Initialise number of available cranes using the SimPy resource.
        self.resource = simpy.Resource(env=self.env, capacity=resources)

        # Add new instance to list of instances.
        InstallationVessel.instances.append(self)

    def execute_activities(self):

        # Manually adjust these!
        sail_length = lognorm(mean=3600 * 1.9, std=1800)
        sail_between_length = lognorm(mean=3600 * 0.5, std=300)
        load_length = lognorm(mean=3600 * 3.7, std=600)
        install_length = lognorm(mean=3600 * (33.2), std=3600)

        while self.port.container.level > 0:

            # Request a berth.
            with self.port.resource.request() as req:

                self.log.entry(description=f'Request berth at {self.port.ID}',
                               activity_state=ActivityState.REQUESTED,
                               **self.__dict__)

                yield req

                self.log.entry(description=f'Request berth at {self.port.ID}',
                               activity_state=ActivityState.GRANTED,
                               **self.__dict__)

                # Check if loading is necessary, if, do so until reached max.
                while self.container.level < self.container.capacity:

                    # Start loading process.
                    load_component = LoadComponent(origin=self.port,
                                                   destination=self,
                                                   length=load_length.rvs(),
                                                   **self.__dict__)
                    yield self.env.process(load_component.execute())

                    if self.port.container.level == 0:
                        break  # Leave loop in case the stock is empty.

            # Navigate from port to the offshore site.
            sail_to = Cruise(origin=self.port, destination=self.owf,
                             length=sail_length.rvs(), **self.__dict__)
            yield self.env.process(sail_to.execute())

            # Install components
            while self.container.level > 0:

                # Install a single component
                length = install_length.rvs()
                w = RequestWeatherWindow(**self.__dict__)
                def limit(tp, hs): return hs > 10 * np.exp(-tp / 2.5)
                yield self.env.process(w.execute(limit_expr=limit,
                                                 duration=length))

                install_component = InstallComponent(
                    origin=self,
                    destination=self.owf,
                    length=length,
                    **self.__dict__
                )
                yield self.env.process(install_component.execute())

                # Sail to the next site
                sail_to = Cruise(origin=self.owf, destination=self.owf,
                                 length=sail_between_length.rvs(),
                                 **self.__dict__)
                yield self.env.process(sail_to.execute())

            # Navigate from the offshore site to port.
            sail_to = Cruise(origin=self.owf, destination=self.port,
                             length=sail_length.rvs(), **self.__dict__)
            yield self.env.process(sail_to.execute())


# ----------------------------------------------------------------------------!
class AEOLUS(InstallationVessel):
    pass


# ----------------------------------------------------------------------------!
class SVANEN(InstallationVessel):
    pass
