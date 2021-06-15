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
from utils import get_event_log, resultant_vector

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

        # Find response motions of tower.
        self.HM = HydroModel(
            parse_waves="./data/raw/HKZ_3.970372E_52.014651N.csv",
            parse_raos="./data/raw/RAO.xlsx",
        )

        if isinstance(kind, str) and kind == "response_motions":
            response_motions = self.HM.response_motions()

            # Limit expression.
            self.limits = lambda displacement: displacement >= 0.03

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
                {"id": "tower", "level": 0, "capacity": 4},
                {"id": "nacelle", "level": 0, "capacity": 4},
                {"id": "blade", "level": 0, "capacity": 4 * 3},
            ],
            nr_resources=1,
            loading_rate=1,
            unloading_rate=1,
            compute_v=10,
        )

    def define_processes(self, *args, **kwargs):
        """Define DES-processes."""

        # Define transit activities.
        self.transit_to_site = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="Transit from port to site",
            duration=3600 * 6,  # Rotterdam -> Borssele [hrs].
            mover=self.aeolus,
            destination=self.owf,
        )

        self.transit_to_port = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="Transit from site to port",
            duration=3600 * 6,  # Borssele -> Rotterdam [hrs].
            mover=self.aeolus,
            destination=self.port,
        )

        # Define loading cycle.
        self.load_towers = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Load towers",
            duration=4 * 3 * 3600,
            processor=self.aeolus,
            origin=self.port,
            destination=self.aeolus,
            amount=1 * 4,
            id_="tower",
        )

        self.load_nacelles = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Load nacelles",
            duration=4 * 3 * 3600,
            processor=self.aeolus,
            origin=self.port,
            destination=self.aeolus,
            amount=1 * 4,
            id_="nacelle",
        )

        self.load_blades = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="Load blades",
            duration=4 * 3600,
            processor=self.aeolus,
            origin=self.port,
            destination=self.aeolus,
            amount=3 * 4,
            id_="blade",
        )

        self.load_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="Load cycle",
            sub_processes=[self.load_towers, self.load_nacelles, self.load_blades],
            condition_event={
                "or": [
                    {
                        "type": "container",
                        "concept": self.aeolus,
                        "state": "full",
                        "id_": "blade",
                    },
                    {
                        "type": "container",
                        "concept": self.port,
                        "state": "empty",
                        "id_": "blade",
                    },
                ]
            },
        )

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

        self.install_blades = TransferObject(
            env=self.env,
            registry=self.registry,
            name="Install blades",
            duration=3 * 3600,
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            amount=3,
            id_="blade",
            weather_resource=self.weather_resource,
            limit_expr=self.limits,
        )

        self.install_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="Install cycle",
            sub_processes=[
                self.positioning,
                self.jacking_up,
                self.install_tower,
                self.install_nacelle,
                self.install_blades,
                self.jacking_down,
            ],
            condition_event={
                "or": [
                    {
                        "type": "container",
                        "concept": self.aeolus,
                        "state": "empty",
                        "id_": "blade",
                    },
                    {
                        "type": "container",
                        "concept": self.owf,
                        "state": "full",
                        "id_": "blade",
                    },
                ]
            },
        )

        # Define full cycle
        self.project_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="Project cycle",
            sub_processes=[
                self.load_cycle,
                self.transit_to_site,
                self.install_cycle,
                self.transit_to_port,
            ],
            condition_event={
                "or": [
                    {
                        "type": "container",
                        "concept": self.port,
                        "state": "empty",
                        "id_": "blade",
                    },
                    {
                        "type": "container",
                        "concept": self.owf,
                        "state": "full",
                        "id_": "blade",
                    },
                ]
            },
        )

        model.register_processes([self.project_cycle])

        self.proc = [
            self.transit_to_port,
            self.transit_to_site,
            self.load_towers,
            self.load_nacelles,
            self.load_blades,
            self.positioning,
            self.jacking_up,
            self.jacking_down,
            self.install_tower,
            self.install_nacelle,
            self.install_blades,
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
class HydroModel(object):
    def __init__(
        self, parse_waves: str = None, parse_raos: str = None, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        # Try to import wave dataset.
        if isinstance(parse_waves, str) and os.path.isfile(parse_waves):
            try:
                self.waves_dataframe = self.parse_wave_data(file=parse_waves)
            except Exception as e:
                logger.debug(msg="Import of wave data went wrong.", exc_info=e)
                self.waves_dataframe = None

        # Try to import structure RAOs.
        if isinstance(parse_raos, str) and os.path.isfile(parse_raos):
            try:
                self.RAOs = self.parse_rao(file=parse_raos)
            except Exception as e:
                logger.debug(msg="Import of RAOs went wrong.", exc_info=e)
                self.RAOs = None

        # Try to combine both datasets.
        if (
            hasattr(self, "RAOs")
            and isinstance(self.RAOs, (pd.DataFrame, xr.DataArray))
            and isinstance(self.waves_dataframe, (pd.DataFrame, xr.DataArray))
        ):
            try:
                self.data = self.build_dataset()
            except Exception as e:
                logger.debug(
                    msg="Combining of RAOs and wave data went wrong", exc_info=e
                )

    def parse_wave_data(self, file, *args, **kwargs):
        """Read the contents of a DHI wave data file."""
        # Make sure not to reload the data.
        if hasattr(self, "wave"):
            return self.wave

        # Import wave data.
        df = pd.read_csv(
            file,
            skiprows=[0],
            parse_dates={"datetime": ["YYYY", "M", "D", "HH", "MM", "SS"]},
            date_parser=lambda x: dt.datetime.strptime(x, "%Y %m %d %H %M %S"),
        ).set_index("datetime")

        # Return the result.
        return df

    def parse_rao(self, file, *args, **kwargs):
        """Read the contents of a response amplitude operator file."""
        # Make sure not to reload the data.
        if hasattr(self, "RAO"):
            return self.RAO

        df = pd.read_excel(file, skiprows=[0, 2])
        df = df.set_index("Tp")
        df.columns = ["RAO"]

        self.hstp_limit = (0.05 / df["RAO"]).to_xarray()

        return df

    def build_dataset(self):
        """Combine wave and RAO data in a xarray.Dataset."""
        # Make sure not to recreate the dataset.
        if hasattr(self, "data"):
            return self.data

        ds = xr.Dataset(
            data_vars=dict(
                wave_data=(["time", "parameter"], self.waves_dataframe),
                tower_rao=(["Tp", "RAO"], self.RAOs),
            ),
            coords=dict(
                time=self.waves_dataframe.index.values,
                parameter=self.waves_dataframe.columns.values,
                Tp=self.RAOs.index.values,
            ),
        )

        return ds

    def response_motions(self, *args, **kwargs):

        # Compute windsea / swell response.
        windsea_resp = (
            self.data["tower_rao"].interp(
                dict(Tp=self.data["wave_data"].sel(dict(parameter="TpWS"))),
                kwargs=dict(fill_value=0),
            )
            * self.data["wave_data"].sel(dict(parameter="Hm0WS"))
        ).values.flatten()

        swell_resp = (
            self.data["tower_rao"].interp(
                dict(Tp=self.data["wave_data"].sel(dict(parameter="TpS"))),
                kwargs=dict(fill_value=0),
            )
            * self.data["wave_data"].sel(dict(parameter="Hm0S"))
        ).values.flatten()

        windsea_angle = (
            self.data["wave_data"].sel(dict(parameter="MWDWS")).values.flatten()
        )
        swell_angle = (
            self.data["wave_data"].sel(dict(parameter="MWDS")).values.flatten()
        )

        # Compute the coupled response.
        total = resultant_vector(windsea_resp, swell_resp, windsea_angle, swell_angle)

        # Make sure to use the largest amplitude.
        choicelist = [windsea_resp, swell_resp, total]
        condlist = [
            windsea_resp >= total,
            swell_resp >= total,
            (windsea_resp < total) & (swell_resp < total),
        ]
        motion = np.select(condlist=condlist, choicelist=choicelist)

        df = pd.DataFrame(
            data=self.data["wave_data"].values,
            columns=self.data["parameter"].values,
            index=self.data["time"].values,
        ).rename_axis("datetime")

        df["displacement"] = motion

        return df

    def sea_state_limit_expression(self, Hm0, Tp, *args, **kwargs):
        hs_lim = self.hstp_limit.interp(dict(Tp=Tp), kwargs=dict(fill_value=0))
        return Hm0 >= hs_lim


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