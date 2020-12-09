''' CONTAINS MAIN SIMULATION ENVIRONMENT. '''
# ----------------------------------------------------------------------------!
import simpy
import datetime
import pandas as pd
from .log import EventLog
from .sites import Site
from .equipment import InstallationVessel


# ----------------------------------------------------------------------------!
class DiscreteEventSimulation(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object of the main simulation environment for simulating
        the installation process of an offshore wind farm. Using the
        corresponding class methods the simulation may be controlled,
        started and event logs and project length can be extracted.
    -------------------------------------------------------------------
    Parameters:
        start_date: datetime.datetime
            Starting date of the construction period.
    -------------------------------------------------------------------
    Class methods:
        .crete_entities()
            Python function for creating and adding entities to the
            simulation.
        .start_simulation()
            Start the simulation environment when called on.
        .get_event_log()
            Returns the event/activity log.
        .get_project_length()
            Returns the expected project length.
    -------------------------------------------------------------------
    '''
    def __init__(self, start_date: datetime.datetime = None, **kwargs):

        # Turn arguments to class attributes
        self.__dict__ = locals()
        del self.__dict__['self']

        # Initialise simulation environment using the SimPy framework
        if not start_date:  # If user did not specify a start date
            self.start_date = datetime.datetime(2021, 1, 1)  # Default date
        self.POSIX = self.start_date.timestamp()  # Turn datetime to POSIX
        self.env = simpy.Environment(initial_time=self.POSIX)

        # Event log
        self.log = EventLog(env=self.env)

    def create_entities(self):
        '''
        ---------------------------------------------------------------
        Description:
            Python function for generating/modelling 'entities' that
            are present during the installation process. These may be
            sites, such as ports and the wind farm itself, but also
            equipment, etc. Using keyword arguments, the user may
            specify the input parameters.
        ---------------------------------------------------------------
        PARAMETERS:
            owf: dict
                A python dictionary containing input variables
                describing the offshore wind farm (ID, size, etc.)
        ---------------------------------------------------------------
        '''
        size = 50

        self.port = Site(ID='CHERBOURG-OCTEVILLE', env=self.env, capacity=size,
                         level=size, resources=1)

        self.owf = Site(ID='SAINT BRIEUC OFFSHORE WIND FARM', env=self.env,
                        capacity=size, level=0, resources=1)

        aeolus = dict(ID='AEOLUS', capacity=5, level=0, resources=1)
        aeolus = InstallationVessel(**aeolus, **self.__dict__)

        # svanen = dict(ID='SVANEN', capacity=5, level=0, resources=1)
        # svanen = InstallationVessel(**svanen, **self.__dict__)

        return locals()

    def start_simulation(self):

        for obj in InstallationVessel.instances:
            self.env.process(obj.execute_activities())

        self.env.run()

        InstallationVessel.instances = []

    def get_event_log(self):
        return pd.DataFrame(self.log.log)

    def get_project_length(self):
        pass


# ----------------------------------------------------------------------------!
