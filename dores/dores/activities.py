''' CONTAINS INSTALLATION ACTIVITIES CARRIED OUT BY INSTALLATION EQUIPMENT. '''
# ----------------------------------------------------------------------------!
from __future__ import annotations
from os import environ

import simpy
from datetime import datetime as dt
from .log import EventLog
from .log import ActivityState

from typing import Callable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .equipment import InstallationVessel
    from .sites import Site
    from .offshore import OffshoreEnvironment


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


class RequestWeatherWindow(object):

    def __init__(self, env: simpy.Environment, log: EventLog, ID: str,
                 port: Site, equipment: InstallationVessel, owf: Site,
                 oe: OffshoreEnvironment, **kwargs):

        self.__dict__ = locals()
        del self.__dict__['self']

    def execute(self, limit_expr: Callable, duration: float):

        window = self.oe.get_windows(limit_expr=limit_expr, duration=duration)
        start_date = window.BeginDate
        end_date = dt.fromtimestamp(self.env.now)
        weather_delay = (start_date - end_date).total_seconds()

        self.description = 'Request sufficient weather window'

        self.log.entry(activity_state=ActivityState.REQUESTED, **self.__dict__)
        yield self.env.timeout(weather_delay)
        self.log.entry(activity_state=ActivityState.GRANTED, **self.__dict__)
