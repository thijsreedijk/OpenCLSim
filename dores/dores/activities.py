''' CONTAINS INSTALLATION ACTIVITIES CARRIED OUT BY INSTALLATION EQUIPMENT. '''
# ----------------------------------------------------------------------------!
from __future__ import annotations

import simpy
from .log import EventLog
from .log import ActivityState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .equipment import InstallationVessel
    from .sites import Site


# ----------------------------------------------------------------------------!
class Cruise(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object describing the sailing activity of an
        installation vessel.
    -------------------------------------------------------------------
    '''
    def __init__(self, env: simpy.Environment, log: EventLog, owf: Site,
                 equipment: InstallationVessel, port: Site, origin: Site,
                 destination: Site, length: int, **kwargs):

        # Class attributes
        self.__dict__ = locals()
        del self.__dict__['self']

        self.description = f'Navigate from {origin.ID} to {destination.ID}'

    def execute(self):

        # Send initialise message to activity log
        self.log.entry(activity_state=ActivityState.INITIATED, **self.__dict__)

        # Perform activity
        yield self.env.timeout(self.length)

        # Send complete message to activity log
        self.log.entry(activity_state=ActivityState.COMPLETED, **self.__dict__)


# ----------------------------------------------------------------------------!
class LoadComponent(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object describing the loading activity of components
        onto an installation vessel.
    -------------------------------------------------------------------
    '''
    def __init__(self, env: simpy.Environment, log: EventLog, owf: Site,
                 equipment: InstallationVessel, port: Site, origin: Site,
                 destination: Site, length: int, **kwargs):

        # Class attributes
        self.__dict__ = locals()
        del self.__dict__['self']

        message = f'Load component from {origin.ID} to {destination.ID}'
        self.description = message

    def execute(self):

        # Send initialise message to activity log
        self.log.entry(activity_state=ActivityState.INITIATED, **self.__dict__)

        # Perform activity
        yield self.origin.container.get(1)
        yield self.destination.container.put(1)
        yield self.env.timeout(self.length)

        # Send complete message to activity log
        self.log.entry(activity_state=ActivityState.COMPLETED, **self.__dict__)


# ----------------------------------------------------------------------------!
class InstallComponent(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object describing the installation activity of
        components.
    -------------------------------------------------------------------
    '''
    def __init__(self, env: simpy.Environment, log: EventLog, owf: Site,
                 equipment: InstallationVessel, port: Site, origin: Site,
                 destination: Site, length: int, **kwargs):

        # Class attributes
        self.__dict__ = locals()
        del self.__dict__['self']

        message = f'Install component from {origin.ID} to {destination.ID}'
        self.description = message

    def execute(self):

        # Send initialise message to activity log
        self.log.entry(activity_state=ActivityState.INITIATED, **self.__dict__)

        # Perform activity
        yield self.origin.container.get(1)
        yield self.destination.container.put(1)
        yield self.env.timeout(self.length)

        # Send complete message to activity log
        self.log.entry(activity_state=ActivityState.COMPLETED, **self.__dict__)
