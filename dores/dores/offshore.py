''' CONTAINS CLASS FOR SIMULATING THE OFFSHORE ENVIRONMENT. '''
# ----------------------------------------------------------------------------!
import simpy
import pandas as pd
import numpy as np
from datetime import datetime as dt

from typing import Callable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
                 hs: list = None, tp: list = None, **kwargs):

        # Class attributes
        self.__dict__ = locals()

        # Check if any data is given, else create NaN list
        if hs is None:
            hs = [np.NaN for x in range(len(date_list))]

        if tp is None:
            tp = [np.NaN for x in range(len(date_list))]

        # Create a metocean database
        self.met = pd.DataFrame({'date': date_list, 'Hs': hs, 'Tp': tp})
        self.met = self.met.set_index('date')

    def get_windows(self, limit_expr: Callable, duration: float, **kwargs):
        '''
        ---------------------------------------------------------------
        Description:
            Python function for obtaining the workable weather windows
            given an activitiy specific limit and duration.
        ---------------------------------------------------------------
        Parameters:
            limit_expr : function(tp, hs)
                A Python function taking the significant wave height
                and peak wave period as input arguments for computing
                whether or not the limit has been exceeded.
            duration : float
                Length of the corresponding activity in seconds [sec].
        ---------------------------------------------------------------
        '''
        met = self.met

        # Check if the limit is exceeded, true if so.
        met['limit'] = limit_expr(met['Tp'], met['Hs'])

        # Create consecutive limit blocks
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
