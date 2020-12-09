''' CONTAINS CLASSES FOR GENERATING ENTITIES. '''
# ----------------------------------------------------------------------------!
import simpy
from .log import (EventLog, ActivityState)
from .sites import Site
from .activities import Cruise, LoadComponent, InstallComponent


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
                 owf: Site, port: Site, capacity: int, level: int,
                 resources: int, **kwargs):

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
                                                   length=3600,
                                                   **self.__dict__)
                    yield self.env.process(load_component.execute())

                    if self.port.container.level == 0:
                        break  # Leave loop in case the stock is empty.

            # Navigate from port to the offshore site.
            sail_to = Cruise(origin=self.port, destination=self.owf,
                             length=3600, **self.__dict__)
            yield self.env.process(sail_to.execute())

            # Install components
            while self.container.level > 0:

                # Install a single component
                install_component = InstallComponent(origin=self,
                                                     destination=self.owf,
                                                     length=3600,
                                                     **self.__dict__)
                yield self.env.process(install_component.execute())

                # Sail to the next site
                sail_to = Cruise(origin=self.owf, destination=self.owf,
                                 length=3600, **self.__dict__)
                yield self.env.process(sail_to.execute())

            # Navigate from the offshore site to port.
            sail_to = Cruise(origin=self.owf, destination=self.port,
                             length=3600, **self.__dict__)
            yield self.env.process(sail_to.execute())


# ----------------------------------------------------------------------------!
class AEOLUS(InstallationVessel):
    pass


# ----------------------------------------------------------------------------!
class SVANEN(InstallationVessel):
    pass
