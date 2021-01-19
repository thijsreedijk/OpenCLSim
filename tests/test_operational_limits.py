"""A simple test of the operational limits plugin activity."""
# -------------------------------------------------------------------------------------!
# Import dependencies
import datetime
import os

import dateutil
import numpy as np
import pandas as pd
import simpy

import openclsim.appendix as appendix
import openclsim.model as model
import openclsim.plugins as plugins

from .test_utils import assert_log


# -------------------------------------------------------------------------------------!
def exec():
    """Test the simulation objects."""
    # Create some sample data for testing purposes.
    cdir = create_sample_data()

    # Create an instance of the simulation environment.
    sim = SimulationEnvironment(start_date=datetime.datetime(2021, 1, 1))

    # Execute simulation command.
    sim.execute_simulation()

    # Test if all went right.
    assert_log(sim.activities[0])  # Tests the activity log on bugs.

    start = sim.event_log[sim.event_log["ActivityState"] == "START"].Timestamp
    hs = sim.oe.hs.loc[start]  # Get the value for hs and tp and test.
    tp = sim.oe.tp.loc[start]  # if its indeed below the threshold.

    hs = hs.iloc[0].values[0]  # Unpacks series to float.
    tp = tp.iloc[0].values[0]  # Unpacks series to float.

    assert not limit_expression(hs, tp)  # Actual test.

    # Display output.
    print("-" * 72)
    print("TESTS WENT ALL FINE.\n")
    print(sim.event_log)
    print("-" * 72)

    # Remove data files.
    os.remove(cdir + "/data/unit_hs.csv")
    os.remove(cdir + "/data/unit_tp.csv")


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
            "duration": 3600,  # Time in seconds it takes to finish.
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
    """
    Model a simple activity with operational limits.

    An instance of the `BasicActivity` class holds the required
    activity parameters for the model to be processed. The class sets up
    the framework for defining activities. The `model.BasicActivity`
    parent class provides the main part of the framework, the
    `plugins.HasRequestWindowPluginActivity` adds the feature of
    operational limits to the activity.

    Parameters
    ----------
        env: simpy.Environment
            A SimPy simulation environment.
        registry: dict
            A dictionary in which the activities are stored.
        name: str
            A descriptive name for storing the activity in the log.
        duration: int
            The number of seconds it takes to execute the activity.
        offshore_environment: plugins.OffshoreEnvironment
            An instance of the OffshoreEnvironment.
        limit_expr: Callable
            A Python function expressing the operational limits in
            terms of offshore environment parameters. See an example
            below.
    """

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
    tp_df = pd.DataFrame({"date": dates, "tp": tp_values}).set_index("date")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    hs_df.to_csv(current_dir + "/data/unit_hs.csv")
    tp_df.to_csv(current_dir + "/data/unit_tp.csv")

    return current_dir


# -------------------------------------------------------------------------------------!
if __name__ == "__main__":
    exec()
