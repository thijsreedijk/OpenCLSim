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
from numpy.lib.function_base import disp
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
            self.start_date = dt.datetime(2018, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

    def resources(self, kind="response_motions", *args, **kwargs):
        """Define the DES-resources."""
        self.weather_resource = plugins.WeatherResource()

        # Find response motions of tower.
        self.HM = HydroModel(
            parse_waves="./data/raw/HKZ_3.970372E_52.014651N.csv",
            parse_raos="./data/raw/Tower_RAO.xlsx",
        )

        if isinstance(kind, str) and kind == "response_motions":
            response_motions = self.HM.response_motions()

            # Limit expression.
            self.limits = lambda displacement: displacement >= 0.05

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
            name="Borssele Offshore Wind Farm",
            geometry=shapely.geometry.Point(0, 0),
            store_capacity=2,
            initials=[
                {"id": "Deep Dig-It", "level": 0, "capacity": 1},
                {"id": "Cable segments", "level": 0, "capacity": self.cable_segments},
            ],
            nr_resources=1,
        )

    def define_equipment(self, MPI_RAO=None, *args, **kwargs):

        pass

    def processes(self, *args, **kwargs):
        """Define DES-processes."""

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

        df = pd.read_excel(file, skiprows=[1])
        df = df.set_index("Tp")
        df.columns = ["RAO"]

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
        )

        df["displacement"] = motion

        return df


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
