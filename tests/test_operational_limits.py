"""A simple test of the operational limits plugin activity."""
# -------------------------------------------------------------------------------------!
# Import dependencies
import datetime
import dateutil
import numpy as np

import openclsim.appendix as appendix
import openclsim.model as model
import openclsim.plugins as plugins

import os
import pandas as pd
import simpy


# -------------------------------------------------------------------------------------!
def main():
    """Test the simulation objects."""
    # Create some sample data for testing purposes
    create_sample_data()

    # Create an instance of the simulation environment
    sim = SimulationEnvironment(start_date=datetime.datetime(2021, 1, 1))

    # Execute simulation command
    sim.execute_simulation()

    # Print the event log
    print(sim.event_log)


# -------------------------------------------------------------------------------------!
# Create a simulation environment
class SimulationEnvironment(object):
    """
    An OpenCLSim simulation object.

    In this example, a basic activity is modelled using the
    `model.BasicActivity` class. However, the activity is constrained
    to operational limits and may, therefore, only start when the
    offshore conditions are safe. The offshore environment is modelled
    using the `plugins.OffshoreEnvironment` and the corresponding
    waiting on weather event/activity is modelled using the plugin:
    `plugins.HasRequestWindowPluginActivity`.

    Parameters
    ----------
        start_date: datetime.datetime
            A datetime object specifying the simulation start date.
    """

    def __init__(self, start_date: datetime.datetime):
        """Set the simulation environment."""
        # Define start date and time of simulation
        self.start_date = start_date
        start_utc = start_date.replace(tzinfo=dateutil.tz.UTC)
        start_epoch = start_utc.timestamp()

        # Initialise a SimPy simulation environment
        self.env = simpy.Environment(initial_time=start_epoch)
        self.registry = {}

    def setup_offshore_environment(self):
        """Create an instance of the offshore environment."""
        # Create instance `OE` (Offshore Environment).
        oe = plugins.OffshoreEnvironment()

        # Store information and data in the instance.
        current_dir = os.path.dirname(os.path.abspath(__file__))

        oe.store_information(var="ID", value="UNIT TEST SITE")
        oe.store_information(var="hs", filename=current_dir + "/data/unit_hs.csv")
        oe.store_information(var="tp", filename=current_dir + "/data/unit_tp.csv")

        # Set offshore environment as class attribute
        self.oe = oe

        return

    def define_activities(self):
        """Use this function to define our activities."""
        # Define activity parameters
        params = {
            "env": self.env,  # The SimPy simulation environment.
            "registry": self.registry,  # For logging purposes mainly.
            "name": "A basic activity",  # Allows us to identify.
            "limit_expr": limit_expression,  # Sets the constrains (see below).
            "offshore_environment": self.oe,  # Defines the OE.
            "duration": 3600 * 3,  # Time in seconds it takes to finish.
        }

        # Setup the activity
        activity = BasicActivity(**params)

        # Register the activity
        model.register_processes([activity])

        return [activity]

    def execute_simulation(self):
        """Start the simulation."""
        self.setup_offshore_environment()
        self.activities = self.define_activities()
        self.env.run()
        return "SUCCESSFUL"

    @property
    def event_log(self):
        """Return the event log."""
        return appendix.get_event_log(activity_list=self.activities)

    @property
    def project_length(self):
        """Return the project length."""
        log = self.event_log
        dt = log.Timestamp.iloc[-1] - log.Timestamp.iloc[0]
        return dt.total_seconds() / (3600)


# -------------------------------------------------------------------------------------!
class BasicActivity(plugins.HasRequestWindowPluginActivity, model.BasicActivity):
    """Model a simple activity with operational limits."""

    def __init__(self, **kwargs):
        """Class constructor."""
        super().__init__(**kwargs)


# -------------------------------------------------------------------------------------!
# Define the operational limits
def limit_expression(hs, tp):
    """
    Define the operational limits as a python function.

    Using Python functions, we can set the conditions for which
    the operations may not be performed. The function should
    return a `True` value to indicate that the operational limit
    has been exceeded for a given combination of input
    parameters.

    """
    # if Hs OR Tp is greater than 0.50, the limit is exceeded.
    return (hs > 0.5) | (tp > 0.5)


# -------------------------------------------------------------------------------------!
def create_sample_data():
    """Create sample data for the test simulation."""
    # Generate sample dates
    dates = np.arange(
        start=datetime.datetime(2021, 1, 1),
        stop=datetime.datetime(2021, 1, 2),
        step=datetime.timedelta(hours=1),
    )

    # Generate sample data and export to *.csv
    hs_values = np.random.random(size=(len(dates)))
    tp_values = np.random.random(size=(len(dates)))

    hs_df = pd.DataFrame({"date": dates, "hs": hs_values}).set_index("date")
    tp_df = pd.DataFrame({"date": dates, "hs": hs_values}).set_index("date")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    hs_df.to_csv(current_dir + "/data/unit_hs.csv")
    tp_df.to_csv(current_dir + "/data/unit_tp.csv")

    return


# -------------------------------------------------------------------------------------!
if __name__ == "__main__":
    main()
