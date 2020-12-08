# ----------------------------------------------------------------------------!
import simpy
from datetime import datetime as dt


# ----------------------------------------------------------------------------!
class EventLog(object):
    def __init__(self, env: simpy.Environment, **kwargs):

        self.env = env
        self.log = {
            'Timestamp': [],
            'ID': [],
            'Description': [],
            'Activity state': [],
            'Stock': [],
            'Onboard': [],
            'Installed': [],
        }

    def entry(self, ID, description, activity_state, port, container, owf,
              **kwargs):
        self.log['Timestamp'].append(dt.fromtimestamp(self.env.now))
        self.log['ID'].append(ID)
        self.log['Description'].append(description)
        self.log['Activity state'].append(activity_state)
        self.log['Stock'].append(port.container.level)
        self.log['Onboard'].append(container.level)
        self.log['Installed'].append(owf.container.level)
