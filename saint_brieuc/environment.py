# ----------------------------------------------------------------------------!
import simpy
from datetime import datetime as dt
import pandas as pd
from log import EventLog
from sites import Site
from vessel import Vessel
from offshore import OffshoreEnvironment


# ----------------------------------------------------------------------------!
class DiscreteEventSimulation(object):
    def __init__(self, start_date: dt = dt(2021, 1, 1), size: int = 54,
                 **kwargs):
        '''
        ---------------------------------------------------------------
        DESCRIPTION:
            Main simulation environment for simulating the installation
            process of an offshore wind farm. Using the corresponding
            class methods the simulation may be started and event logs
            can be extracted.
        ---------------------------------------------------------------
        PARAMETERS:
            start_date [datetime.datetime]: Project's start date.
            size [int]: Size of the offshore wind farm (no. turbines).
        ---------------------------------------------------------------
        CLASS METHODS:
            .start_simulation(): Runs the simulation.
            .get_event_log(): Returns the activity/event log.
            .get_project_length(): Returns the estimated project length.
        ---------------------------------------------------------------
        '''
        self.start_date = start_date
        self.size = size

        self.env = simpy.Environment(initial_time=start_date.timestamp())
        self.log = EventLog(**self.__dict__)

        if 'dates' and 'hs' in kwargs:
            self.offshore_env = True
            self.dates = kwargs['dates']
            self.hs = kwargs['hs']
            self.oe = OffshoreEnvironment(**self.__dict__)
        else:
            self.offshore_env = False
            self.oe = None

        self.entities = self.create_entities()

    def create_entities(self):
        self.port = Site(ID='Saint Brieuc Port', capacity=self.size,
                         level=self.size, **self.__dict__)
        self.owf = Site(ID='Saint Brieuc OWF', capacity=self.size, level=0,
                        **self.__dict__)

        self.aeolus = Vessel(ID='Aeolus', **self.__dict__)

        return locals()

    def start_simulation(self):
        for obj in Vessel.instances:
            self.env.process(obj.execute_actions())

        self.env.run()

        Vessel.instances = []

    def get_event_log(self):
        return pd.DataFrame(self.log.log)

    def get_project_length(self):
        log_file = self.log.log
        period = log_file['Timestamp'][-1] - log_file['Timestamp'][0]
        period = period.total_seconds() / (24 * 3600)
        return period
