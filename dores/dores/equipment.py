''' CONTAINS CLASSES FOR GENERATING ENTITIES. '''
# ----------------------------------------------------------------------------!
import simpy
from .log import (EventLog, ActivityState)
from .sites import Site


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

        # Assign arguments to class attributes
        self.__dict__ = locals()
        self.__dict__['equipment'] = self.__dict__.pop('self')

        # Initialise deck container using the SimPy container
        self.container = simpy.Container(env=self.env, capacity=capacity,
                                         init=level)

        # Initialise number of available cranes using the SimPy resource
        self.resource = simpy.Resource(env=self.env, capacity=resources)

        # Add new instance to list of instances
        InstallationVessel.instances.append(self)

    def execute_activities(self):

        while True:

            # Load components onto vessel's deck
            yield self.env.process(self.load_component(destination=self,
                                                       origin=self.port))

            # Sail from the port to the construction site
            yield self.env.process(self.navigate(destination=self.owf,
                                                 origin=self.port))

            # Install component(s)
            while True:

                # Actually install one
                yield self.env.process(
                    self.install_component(
                        destination=self.owf,
                        origin=self
                    )
                )

                if not self.container.level > 0:
                    break  # If no more components on deck leave the loop

                # Sail to the next site
                yield self.env.process(self.navigate(destination=self.owf,
                                                     origin=self.owf))

            # Sail from the offshore site to port
            yield self.env.process(self.navigate(destination=self.port,
                                                 origin=self.owf))

            if self.port.container.level == 0:
                break

    def navigate(self, destination: Site, origin: Site):

        # Get location IDs
        destination = destination.ID
        origin = origin.ID

        # Send initialise message to activity log
        self.log.entry(description=f'Navigate from {origin} to {destination}',
                       activity_state=ActivityState.INITIATED,
                       **self.__dict__)

        # Perform activity
        yield self.env.timeout(3600)

        # Send complete message to activity log
        self.log.entry(description=f'Navigate from {origin} to {destination}',
                       activity_state=ActivityState.COMPLETED,
                       **self.__dict__)

    def load_component(self, destination, origin):

        # Get location IDs
        dest = destination.ID
        orig = origin.ID

        # Request a berth
        with origin.resource.request() as req:
            self.log.entry(description=f'Request berth at {orig}',
                           activity_state=ActivityState.REQUESTED,
                           **self.__dict__)
            yield req
            self.log.entry(description=f'Request berth at {orig}',
                           activity_state=ActivityState.GRANTED,
                           **self.__dict__)

            # Send initialise message to activity log
            message = f'Load component from {orig} onto {dest}'
            self.log.entry(description=message,
                           activity_state=ActivityState.INITIATED,
                           **self.__dict__)

            # Perform activity until deck is full or origin is empty!
            while destination.container.level < destination.container.capacity:

                if origin.container.level == 0:
                    break

                yield origin.container.get(1)
                yield destination.container.put(1)
                yield self.env.timeout(3600)

            # Send initialise message to activity log
            message = f'Load component from {orig} onto {dest}'
            self.log.entry(description=message,
                           activity_state=ActivityState.COMPLETED,
                           **self.__dict__)

    def install_component(self, destination, origin):

        # Get location IDs
        dest = destination.ID
        orig = origin.ID

        # Send initialise message to activity log
        message = f'Install component from {orig} to {dest}'
        self.log.entry(description=message,
                       activity_state=ActivityState.INITIATED,
                       **self.__dict__)

        # Perform activity
        yield origin.container.get(1)
        yield destination.container.put(1)
        yield self.env.timeout(3600)

        # Send initialise message to activity log
        message = f'Install component from {orig} to {dest}'
        self.log.entry(description=message,
                       activity_state=ActivityState.COMPLETED,
                       **self.__dict__)


# ----------------------------------------------------------------------------!
class AEOLUS(InstallationVessel):
    pass


# ----------------------------------------------------------------------------!
class SVANEN(InstallationVessel):
    pass
