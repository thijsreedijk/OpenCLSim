"""OpenCLSim example for multiprocessing."""
# -------------------------------------------------------------------------------------!
import datetime as dt

import dateutil.tz as tz
import numpy as np
import pandas as pd
import shapely
import simpy
from hydro_model import HydroModel
from utils import get_event_log

import openclsim.core as core
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

        # Define activity lengths.
        self.transit_to_site_duration = 4 * 3600  # [sec]
        self.launch_activity_duration = 1 * 3600  # [sec]
        self.recover_activity_duration = 1 * 3600  # [sec]
        self.bury_export_cable_duration = 10 * 3600  # [sec]

        # Define size of the activities.
        self.cable_segments = 25

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
                method="smallest", type="displacements"
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

    def define_sites(self, *args, **kwargs):
        """Define sites involved in construction."""
        # Define port.
        self.port = Site(
            env=self.env,
            name="Port of Rotterdam",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=1,
            initials=[
                {"id": "Cable segments", "level": 0, "capacity": self.cable_segments}
            ],
            nr_resources=1,
        )

        # Define construction site.
        self.owf = Site(
            env=self.env,
            name="Offshore Wind Farm",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=2,
            initials=[
                {"id": "Deep Dig-It", "level": 0, "capacity": 1},
                {"id": "Cable segments", "level": 0, "capacity": self.cable_segments},
            ],
            nr_resources=1,
        )

    def define_equipment(self, MPI_RAO=None, *args, **kwargs):
        # Define the MPI equipment.
        self.mpi = InstallationEquipment(
            env=self.env,
            name="MPI Adventure - Deep Dig-It",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=2,
            initials=[
                {"id": "Deep Dig-It", "level": 1, "capacity": 1},
                {
                    "id": "Cable segments",
                    "level": self.cable_segments,
                    "capacity": self.cable_segments,
                },
            ],
            nr_resources=1,
            loading_rate=1,
            unloading_rate=1,
            compute_v=10,
        )

    def processes(self, *args, **kwargs):
        """Define DES-processes."""

        # Define transit to site activity.
        self.transit_to_site = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="Transit from port to site",
            duration=self.transit_to_site_duration,
            mover=self.mpi,
            destination=self.port,
        )

        self.launch_activity = TransferObject(
            env=self.env,
            registry=self.registry,
            name="Launch Deep Dig-It",
            duration=self.launch_activity_duration,
            processor=self.mpi,
            origin=self.mpi,
            destination=self.owf,
            amount=1,
            id_="Deep Dig-It",
            weather_resource=self.weather_resource,
            limit_expr=self.limits,
        )

        # Define burying activity.
        self.bury_export_cable = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Bury export cable",
            duration=self.bury_export_cable_duration,
            processor=self.mpi,
            origin=self.mpi,
            destination=self.owf,
            amount=1,
            id_="Cable segments",
        )

        # Define recover activity.
        self.recover_activity = TransferObject(
            env=self.env,
            registry=self.registry,
            name="Recover Deep Dig-It",
            duration=self.recover_activity_duration,
            processor=self.mpi,
            origin=self.owf,
            destination=self.mpi,
            amount=1,
            id_="Deep Dig-It",
            weather_resource=self.weather_resource,
            limit_expr=self.limits,
        )

        # Define transit to port activity.
        self.transit_to_port = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="Transit from site to port",
            duration=self.transit_to_site_duration,
            mover=self.mpi,
            destination=self.owf,
        )

        self.smd_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="Launch and Recovery cycle",
            sub_processes=[
                self.launch_activity,
                self.bury_export_cable,
                self.recover_activity,
            ],
            condition_event={
                "or": [
                    {
                        "type": "container",
                        "concept": self.owf,
                        "state": "full",
                        "id_": "Cable segments",
                    },
                    {
                        "type": "container",
                        "concept": self.mpi,
                        "state": "empty",
                        "id_": "Cable segments",
                    },
                ]
            },
        )

        self.cycle = model.SequentialActivity(
            env=self.env,
            registry=self.registry,
            name="Installation sequence",
            sub_processes=[self.transit_to_site, self.smd_cycle, self.transit_to_port],
        )

        # Register activities.
        self.proc = [
            self.transit_to_site,
            self.launch_activity,
            self.bury_export_cable,
            self.recover_activity,
            self.transit_to_port,
        ]

        model.register_processes([self.cycle])

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
        self.define_sites()
        self.define_equipment()
        self.processes()

        # Run simulation.
        self.start_simulation()

    def project_length(self, *args, **kwargs):
        """Retrieve the project length."""
        # Extract the event log.
        log = plot.get_log_dataframe(self.cycle)

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


# -------------------------------------------------------------------------------------!
class TransferObject(plugins.HasRequestWindowPluginActivity, model.ShiftAmountActivity):
    """ShiftAmountActivity with weather plugin."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)


# -------------------------------------------------------------------------------------!
class Site(
    core.Identifiable,
    core.Log,
    core.Locatable,
    core.HasMultiContainer,
    core.HasResource,
):
    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)


# -------------------------------------------------------------------------------------!
class InstallationEquipment(
    core.Identifiable,
    core.Log,
    core.MultiContainerDependentMovable,
    core.Processor,
    core.HasResource,
    core.HasMultiContainer,
    core.LoadingFunction,
    core.UnloadingFunction,
):
    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)
