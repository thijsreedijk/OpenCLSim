''' CONTAINS LOG CLASS FOR TRACKING EVENTS AND ACTIVITIES/PROCESSES. '''
# ----------------------------------------------------------------------------!
from __future__ import annotations
import simpy
import enum
import datetime

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .equipment import InstallationVessel
    from .sites import Site


# ----------------------------------------------------------------------------!
class ActivityState(enum.Enum):

    INITIATED = 0
    COMPLETED = 1
    REQUESTED = 2
    GRANTED = 3
    UNKNOWN = -1


# ----------------------------------------------------------------------------!
class EventLog(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object for tracking activities and events. Using the
        corresponding class methods, the log may be updated or
        retrieved.
    -------------------------------------------------------------------
    Parameters:
        env: simpy.Environment
    -------------------------------------------------------------------
    '''
    def __init__(self, env: simpy.Environment, **kwargs):

        # Allocate arguments to class attributes
        self.__dict__ = locals()

        # Initialise an empty activity log
        self.log = dict(Timestamp=[], ID=[], ActivityDescription=[],
                        ActivityState=[], ComponentsInStock=[],
                        ComponentsOnboard=[], ComponentsInstalled=[])

    def entry(self, owf: Site, equipment: InstallationVessel, port: Site,
              description: str = None, activity_state: ActivityState = None,
              **kwargs):

        current_time = datetime.datetime.fromtimestamp(self.env.now)
        self.log['Timestamp'].append(current_time)
        self.log['ID'].append(equipment.ID)
        self.log['ActivityDescription'].append(description)
        self.log['ActivityState'].append(activity_state.name)
        self.log['ComponentsInStock'].append(port.container.level)
        self.log['ComponentsOnboard'].append(equipment.container.level)
        self.log['ComponentsInstalled'].append(owf.container.level)
