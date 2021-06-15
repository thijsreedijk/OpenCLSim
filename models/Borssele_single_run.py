"""OpenCLSim example for multiprocessing."""
# -------------------------------------------------------------------------------------!
import datetime as dt
import logging
import os

import dateutil.tz as tz
import numpy as np
import pandas as pd
import shapely
import simpy
import xarray as xr
from utils import get_event_log

import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugins

logger = logging.getLogger(__name__)


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
            self.start_date = dt.datetime(2010, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

        self.size = 1

    def resources(self, kind="response_motions", *args, **kwargs):
        """Define the DES-resources."""
        self.weather_resource = plugins.WeatherResource()

        # Import wave data.
        wave_df = pd.read_csv(
            "./data/raw/HKZ_3.970372E_52.014651N.csv",
            skiprows=[0],
            parse_dates={"datetime": ["YYYY", "M", "D", "HH", "MM", "SS"]},
            date_parser=lambda x: dt.datetime.strptime(x, "%Y %m %d %H %M %S"),
        ).set_index("datetime")

        # Remove NaN values.
        cols = (wave_df < 0).any()[lambda x: x].index
        wave_df[cols] = wave_df[cols].where(wave_df[cols] >= 0, 0)

        # Import RAO.
        response_amplitude_operator = pd.read_excel(
            "./data/raw/Tower_RAO.xlsx", skiprows=[0, 2]
        )

        # Build dataset.
        dataset = wave_df.to_xarray()

        dataset["RAO"] = xr.DataArray(
            data=response_amplitude_operator["RAO"],
            dims="freq",
            coords=dict(freq=response_amplitude_operator["Tp"]),
        )

        max_displacement = 0.035  # [m] -> amplitude!

        # If kind == "allowable_sea_state".
        if kind == "allowable_sea_state":

            dataset["Hm0_limit"] = max_displacement / dataset["RAO"]

            def sea_state_limit(Hm0, Tp):
                Hs_limit = dataset["Hm0_limit"].interp(dict(freq=Tp))
                return Hm0 >= Hs_limit

            self.limits = sea_state_limit

            self.weather_resource.store_information(wave_df.reset_index())

        # Elif kind == "response_motions".
        elif kind == "response_motions":

            # Compute response motions.
            dataset["swell_response"] = (
                dataset["RAO"].interp(
                    dict(freq=dataset["TpS"]), kwargs=dict(fill_value=np.nan)
                )
                * dataset["Hm0S"]
            )

            dataset["windsea_response"] = (
                dataset["RAO"].interp(
                    dict(freq=dataset["TpWS"]), kwargs=dict(fill_value=np.nan)
                )
                * dataset["Hm0WS"]
            )

            dataset["total_response"] = (
                dataset["windsea_response"] + dataset["swell_response"]
            )

            dataframe = (
                dataset["total_response"]
                .to_dataframe()
                .rename_axis("datetime")
                .reset_index()
            )

            self.weather_resource.store_information(dataframe)

            self.limits = lambda total_response: total_response >= max_displacement

    def define_sites(self, *args, **kwargs):
        """Define sites involved in construction."""
        # Define port.
        self.port = Site(
            env=self.env,
            name="Port of Rotterdam",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=3,
            initials=[
                {"id": "tower", "level": self.size, "capacity": self.size},
                {"id": "nacelle", "level": self.size, "capacity": self.size},
                {"id": "blade", "level": 3 * self.size, "capacity": 3 * self.size},
            ],
            nr_resources=1,
        )

        # Define construction site.
        self.owf = Site(
            env=self.env,
            name="Borssele Offshore Wind Farm",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=3,
            initials=[
                {"id": "tower", "level": 0, "capacity": self.size},
                {"id": "nacelle", "level": 0, "capacity": self.size},
                {"id": "blade", "level": 0, "capacity": self.size * 3},
            ],
            nr_resources=1,
        )

    def define_equipment(self, *args, **kwargs):
        # Define the Aeolus equipment.
        self.aeolus = InstallationEquipment(
            env=self.env,
            name="Aeolus",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=3,
            initials=[
                {"id": "tower", "level": 1, "capacity": 1},
                {"id": "nacelle", "level": 1, "capacity": 1},
                {"id": "blade", "level": 3, "capacity": 3},
            ],
            nr_resources=1,
            loading_rate=1,
            unloading_rate=1,
            compute_v=10,
        )

    def define_processes(self, *args, **kwargs):
        """Define DES-processes."""

        # Define arriving process.
        self.positioning = model.BasicActivity(
            env=self.env,
            registry=self.registry,
            name="Positioning on site",
            duration=1.5 * 3600,
        )

        self.jacking_up = model.BasicActivity(
            env=self.env,
            registry=self.registry,
            name="Jacking up",
            duration=3.00 * 3600,
        )

        # Define departure process.
        self.jacking_down = model.BasicActivity(
            env=self.env,
            registry=self.registry,
            name="Jacking down",
            duration=1.50 * 3600,
        )

        # Define installation process.
        self.install_tower = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Install tower",
            duration=5 * 3600,
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            amount=1,
            id_="tower",
        )

        self.install_nacelle = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Install nacelle",
            duration=4 * 3600,
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            amount=1,
            id_="nacelle",
        )

        self.install_blade = TransferObject(
            env=self.env,
            registry=self.registry,
            name="Install blades",
            duration=1 * 3600,
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            amount=1,
            id_="blade",
            weather_resource=self.weather_resource,
            limit_expr=self.limits,
        )

        self.install_blades = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="Install blades cycle",
            sub_processes=[self.install_blade],
            condition_event=[
                {
                    "type": "container",
                    "concept": self.aeolus,
                    "state": "empty",
                    "id_": "blade",
                }
            ],
        )

        # Define full cycle
        self.project_cycle = model.SequentialActivity(
            env=self.env,
            registry=self.registry,
            name="Project cycle",
            sub_processes=[
                self.positioning,
                self.jacking_up,
                self.install_tower,
                self.install_nacelle,
                self.install_blades,
                self.jacking_down,
            ],
        )

        model.register_processes([self.project_cycle])

        self.proc = [
            self.positioning,
            self.jacking_up,
            self.jacking_down,
            self.install_tower,
            self.install_nacelle,
            self.install_blade,
        ]

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
        self.define_processes()

        # Run simulation.
        self.start_simulation()

    def project_length(self, *args, **kwargs):
        """Retrieve the project length."""
        # Extract the event log.
        log = plot.get_log_dataframe(self.project_cycle)

        # Find start and stop-dates.
        start = log["Timestamp"].iloc[0]
        stop = log["Timestamp"].iloc[-1]

        # Return the difference.
        return stop - start

    def get_timeline(self, *args, **kwargs):
        """Create a timeline from activity log."""
        # Read out the activities.
        dataframe = get_event_log(
            activity_list=self.proc, entities=[self.aeolus, self.port, self.owf]
        )

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
