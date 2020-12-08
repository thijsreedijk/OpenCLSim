# ----------------------------------------------------------------------------!
import simpy
from datetime import datetime as dt
import pandas as pd
from log import EventLog
from sites import Site


# ----------------------------------------------------------------------------!
class OffshoreEnvironment(object):
    def __init__(self, env: simpy.Environment, dates: list, hs: list,
                 **kwargs):

        self.env = env

        self.met = (pd.DataFrame(data={'date': dates, 'Hs': hs})
                      .set_index('date'))

    def import_data(self, fname):
        pass

    def request_window(self, log: EventLog, ID: str, port: Site,
                       container: simpy.Container, owf: Site, limit: float,
                       duration: float, **kwargs):

        window = self.get_window(limit=limit, duration=duration)
        start_date = window.BeginDate
        end_date = dt.fromtimestamp(self.env.now)
        weather_delay = (start_date - end_date).total_seconds()

        description = 'Requesting a workable weather window'

        var = locals()  # <= Temporal fix
        del var['self']  # <= Temporal fix

        log.entry(activity_state='Requested', **var)
        yield self.env.timeout(weather_delay)
        log.entry(activity_state='Granted', **var)

    def get_window(self, limit: float, duration: float, **kwargs):

        met = self.met
        met['limit'] = met.Hs > limit  # True if limit is exceeded
        met['block'] = (met.limit.shift(1) != met.limit).cumsum()

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
