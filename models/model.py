"""OpenCLSim example for multiprocessing."""
# -------------------------------------------------------------------------------------!
import datetime as dt

import dateutil.tz as tz
import numpy as np
import pandas as pd
import simpy
import xarray as xr

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

    def resources(self, *args, **kwargs):
        """Define the DES-resources."""
        self.weather_resource = plugins.WeatherResource()

        # Import DHI's HKZ dataset.
        HKZ = pd.read_csv(
            "./data/raw/HKZ_3.970372E_52.014651N.csv",
            skiprows=[0],
            parse_dates={"datetime": ["YYYY", "M", "D", "HH", "MM", "SS"]},
            date_parser=lambda x: dt.datetime.strptime(x, "%Y %m %d %H %M %S"),
        )

        self.weather_resource.store_information(data=HKZ)

    def processes(self, limit_expr=None, *args, **kwargs):
        """Define DES-processes."""

        self.process = BasicActivity(
            env=self.env,
            registry=self.registry,
            name="example process.",
            duration=3600,
            weather_resource=self.weather_resource,
            limit_expr=limit_expr,
        )

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


# -------------------------------------------------------------------------------------!
class BasicActivity(plugins.HasRequestWindowPluginActivity, model.BasicActivity):
    """BasicActivity with weather plugin."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)


# -------------------------------------------------------------------------------------!
class HydroDynamicModel(object):
    """Model the vessel motion response to wave loads."""

    def __init__(self, *args, **kwargs) -> None:
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Limits for MPI Adventure lifting operations.
        self.response_limits(
            type=["accelerations", "displacements"],
            surge=[0.1378, np.inf],
            sway=[0.2063, np.inf],
            heave=[0.5115, 1],
            roll=[0.005, np.radians(0.50)],
            pitch=[0.01, np.radians(0.20)],
            yaw=[0.0039, np.inf],
        )

    def irregular_response(self, *args, **kwargs):
        """Estimate the irregular response motions."""
        pass

    def regular_response(
        self, operators, height, period, direction, theta, *args, **kwargs
    ):
        """Estimate the regular motion response."""
        pass

    def limit_expression(self, *args, **kwargs):
        """Define the operational limits."""
        pass

    def response_limits(
        self,
        type: str = "accelerations",  # Otherwise "displacements".
        surge: float = None,  # [m/s²] or [m]
        sway: float = None,  # [m/s²] or [m]
        heave: float = None,  # [m/s²] or [m]
        yaw: float = None,  # [rad/s²] or [rad]
        roll: float = None,  # [rad/s²] or [rad]
        pitch: float = None,  # [rad/s²] or [rad]
        *args,
        **kwargs
    ):
        """Impose response limits."""
        self.motion_limits = pd.DataFrame(
            dict(
                type=type,
                surge=surge,
                sway=sway,
                heave=heave,
                roll=roll,
                pitch=pitch,
                yaw=yaw,
            )
        )
