"""OpenCLSim example for multiprocessing."""
# -------------------------------------------------------------------------------------!
import datetime as dt

import dateutil.tz as tz
import numpy as np
import pandas as pd
import simpy
from hydro_model import HydroModel
from utils import get_event_log

import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugins


# -------------------------------------------------------------------------------------!
class DESModel(object):
    """OpenCLSim DES-model."""

    def __init__(self, start_date: dt.datetime = None, *args, **kwargs):
        """Initialise class object."""
        super().__init__(*args, **kwargs)

        # define simulation environment.
        try:
            self.start_date = start_date.replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()
        except Exception:
            self.start_date = dt.datetime(2018, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

    def resources(self, kind="response_motions", *args, **kwargs):
        """Define the DES-resources."""
        self.weather_resource = plugins.WeatherResource()

        # Setup the hydrodynamic model.
        self.HM = HydroModel(
            parse_raos="./data/preprocessed/MPI_Adventure_RAO.csv",
            parse_waves="./data/raw/HKZ_3.970372E_52.014651N.csv",
            parse_limits="./data/raw/MPI_limits.xlsx",
        )

        # Compute response motions
        if isinstance(kind, str) and kind == "response_motions":
            response_motions = self.HM.response_motions(
                method="mean-wave-dir", type="accelerations"
            )

            # Define limits.
            self.limits = self.HM.RAO_limit_expression

            # Store response motions in resource.
            self.weather_resource.store_information(response_motions.reset_index())

        # Use allowable sea state limits instead.
        elif isinstance(kind, str) and kind == "allowable_sea_state":

            # Define limits.
            self.limits = self.HM.sea_state_limit_expression

            # Store weather conditions in resource.
            self.weather_resource.store_information(
                self.HM.waves_dataframe.reset_index()
            )

    def processes(self, *args, **kwargs):
        """Define DES-processes."""

        self.process = BasicActivity(
            env=self.env,
            registry=self.registry,
            name="example process.",
            duration=3600,
            weather_resource=self.weather_resource,
            limit_expr=self.limits,
        )

        self.proc = [self.process]

        model.register_processes(self.process)

    def start_simulation(self, *args, **kwargs):
        """Start the discrete-event simulation."""
        self.env.run()

    def restart_simulation(self, start_date, *args, **kwargs):
        """Start simulation for a different date."""
        # Redefine simulation environment.
        if hasattr(start_date, "astype"):
            start_date = start_date.astype(dt.datetime)

        try:
            self.start_date = start_date.replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()
        except Exception:
            self.start_date = dt.datetime(2020, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

        # Redefine the processes.
        self.processes()

        # Run simulation.
        self.start_simulation()

    def project_length(self, *args, **kwargs):
        """Retrieve the project length."""
        # Extract the event log.
        log = plot.get_log_dataframe(self.process)

        # Find start and stop-dates.
        start = log["Timestamp"].iloc[0]
        stop = log["Timestamp"].iloc[-1]

        # Return the difference.
        return stop - start

    def get_timeline(self, *args, **kwargs):
        """Create a timeline from activity log."""
        # Read out the activities.
        dataframe = get_event_log(self.proc)

        # Find activity blocks.
        condlist = [
            dataframe["ActivityState"] == "WAIT_START",
            dataframe["ActivityState"] == "START",
            (dataframe["ActivityState"] != "WAIT_START")
            | (dataframe["ActivityState"] != "START"),
        ]
        choicelist = [1, 1, 0]
        dataframe["block"] = np.select(condlist, choicelist).cumsum()

        # Find the waiting on weather events.
        condlist = [
            (dataframe["ActivityState"] == "WAIT_START")
            | (dataframe["ActivityState"] == "WAIT_STOP"),
            (dataframe["ActivityState"] != "WAIT_START")
            & (dataframe["ActivityState"] != "WAIT_STOP"),
        ]
        choicelist = ["Waiting on weather", dataframe["Description"]]

        dataframe["Description"] = np.select(condlist, choicelist)

        # Use groupby to obtain a timeline.
        timeline = pd.DataFrame(
            {
                "start": dataframe.groupby("block")["Timestamp"].first(),
                "stop": dataframe.groupby("block")["Timestamp"].last(),
                "description": dataframe.groupby("block")["Description"].first(),
            }
        )

        # Calculate duration of each.
        timeline["duration"] = timeline["stop"] - timeline["start"]

        # Return timeline
        return timeline

    def get_downtime(self, *args, **kwargs):
        """Compute weather downtime from timeline."""
        # Find timeline.
        timeline = self.get_timeline()

        # Select weather downtime activities.
        selection = timeline.loc[timeline["description"] == "Waiting on weather"]

        # Compute the total downtime duration and return.
        return selection["duration"].sum()


# -------------------------------------------------------------------------------------!
class BasicActivity(plugins.HasRequestWindowPluginActivity, model.BasicActivity):
    """BasicActivity with weather plugin."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)
