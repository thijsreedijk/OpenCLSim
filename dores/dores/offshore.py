''' CONTAINS CLASS FOR SIMULATING THE OFFSHORE ENVIRONMENT. '''
# ----------------------------------------------------------------------------!
import simpy
import pandas as pd
import numpy as np
from datetime import datetime as dt
from .log import EventLog, ActivityState
from .sites import Site
from .equipment import InstallationVessel


# ----------------------------------------------------------------------------!
class OffshoreEnvironment(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object used for representing the offshore environment,
        often abbreviated to 'OE'. The class can be used to define the
        metocean condition, to derive the available weather windows,
        etc.
    -------------------------------------------------------------------
    Parameters:
        env: simpy.Environment
            The SimPy simulation environment.
        date_list: list
            A list of datetime objects corresponding to the dates of
            the data.
        hs: list
            A numeric valued list or array of the significant wave
            height in meters [m].
        tp: list
            A numeric valued list or array of the peak wave period in
            seconds [s].
    -------------------------------------------------------------------
    '''
    def __init__(self, env: simpy.Environment, date_list: list = [],
                 hs: list = [], tp: list = [], **kwargs):

        # Class attributes
        self.__dict__ = locals()

        # Check if any data is given, else create NaN list
        if not hs:
            hs = [np.NaN for x in range(len(date_list))]

        if not tp:
            tp = [np.NaN for x in range(len(date_list))]

        # Create a metocean database
        self.met = pd.DataFrame({'date': date_list, 'Hs': hs, 'Tp': tp})

    def request_window(self, log: EventLog, ID: str, port: Site,
                       equipment: InstallationVessel, owf: Site, limit: float,
                       duration: float, **kwargs):
        '''
        ---------------------------------------------------------------
        Description:
            Python generator for simulating the delay due to metocean
            conditions. Searches for the first available window given
            the activity specific limit and duration.
        ---------------------------------------------------------------
        Parameters:
        ---------------------------------------------------------------
        '''

        window = self.get_window(limit=limit, duration=duration)
        start_date = window.BeginDate
        end_date = dt.fromtimestamp(self.env.now)
        weather_delay = (start_date - end_date).total_seconds()

        self.description = 'Request a workable weather window'

        var = locals()  # <= Temporal fix
        del var['self']  # <= Temporal fix

        log.entry(activity_state=ActivityState.REQUESTED, **var)
        yield self.env.timeout(weather_delay)
        log.entry(activity_state=ActivityState.GRANTED, **var)

    def get_windows(self, limit: float, duration: float, **kwargs):
        '''
        ---------------------------------------------------------------
        Description:
            Python function for obtaining the workable weather windows
            given an activitiy specific limit and duration.
        ---------------------------------------------------------------
        Parameters:
        ---------------------------------------------------------------
        '''
        met = self.met
        met['limit'] = met['Hs'] > limit  # True if limit is exceeded
        met['block'] = (met['limit'].shift(1) != met['limit']).cumsum()

        weather_windows = pd.DataFrame({
            'BeginDate': (met.reset_index()
                             .groupby('block')
                             .date
                             .first()),
            'EndDate': (met.reset_index()
                           .groupby('block')
                           .date.last()),
            'LimitExceeded': (met.groupby('block')
                                 .limit
                                 .first())
        })

        weather_windows['Length'] = ((weather_windows['EndDate'] -
                                      weather_windows['BeginDate'])
                                     .dt.total_seconds() / (3600))

        length = duration / 3600  # <= convert from seconds to hours

        try:
            first = weather_windows[(weather_windows['Length'] > length) &
                                    (~weather_windows['LimitExceeded']) &
                                    (weather_windows['BeginDate'] >=
                                     dt.fromtimestamp(self.env.now))].iloc[0]
        except IndexError:
            print('Oops... no suitable weather window was found.')
            print('\n')
            print('Metocean data might be not long enough!')
            return print(weather_windows)

        self.weather_windows = weather_windows

        return first
