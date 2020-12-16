''' MAIN SIMULATION ENVIRONMENT FOR SIMULATING THE INSTALLATION PROCESS '''
# ----------------------------------------------------------------------------!
import datetime
from shapely.geometry.geo import shape
import simpy
import shapely

from .appendix import remove_item
from .sites import Site
from .equipment import InstallationVessel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import datetime


# ----------------------------------------------------------------------------!
class InstallationModel(object):
    ''' Python object for simulating the installation process.

    Main simulation environment for simulating the installation process
    and those activities involved.

    Parameters
    ----------
        start_date: datetime.datetime
            Initiation date of the construction period.
    '''
    def __init__(self, start_date: 'datetime.datetime' = None, **kwargs):

        # Instance attributes
        self.__dict__ = remove_item(d=locals(), k='kwargs')
        self.__dict__.update(**kwargs)

        # Default or user specified start date
        if start_date is None:
            self.__dict__['start_date'] = datetime.datetime(2021, 1, 1)
        self.POSIX = self.start_date.timestamp()

        # Initialise SimPy framework
        self.env = simpy.Environment(initial_time=self.POSIX)

    def create_equipment(self):
        ''' Python function for modelling offshore equipment.

        Through this function, the user adds 'entities' to the
        simulation environment.

        Parameters
        ----------
        '''
        aeolus = dict(env=self.env, geometry=shapely.geometry.Point(0, 0),
                      name='AEOLUS', level=0.00, v=10.00)

        aeolus = InstallationVessel(**aeolus)

    def create_site(self):
        ''' Python function for modelling an (offshore) site.

        User may define the type of site. Harbour/port or the offshore
        wind farm. Depending on the type, it may require additional
        parameters to be passed through.

        Parameters
        ----------
        '''
        port = Site(capacity=10, env=self.env, level=10, name='CHERBOURG')

    def get_eventlog(self):
        ''' Python function returns the event/activity log.

        Returns the event/activity log of the simulation. Note:
        the function requires the simulation to be executed. Else, an
        empty log is returned.

        Parameters
        ----------
        '''
        pass

    def get_project_length(self):
        ''' Python function returns the total installation time.

        When called on, function returns the estimated project length
        in days. Note: simulation should have been executed already.

        Parameters
        ----------
        '''
        pass

    def start_simulation(self):
        ''' Python function for initiation of the simulation.

        Function runs the SimPy environment.

        Parameters
        ----------
        '''
        pass


# ----------------------------------------------------------------------------!
