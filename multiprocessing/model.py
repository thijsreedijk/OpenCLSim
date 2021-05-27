"""OpenCLSim example for multiprocessing."""
# -------------------------------------------------------------------------------------!
import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugins
import numpy as np
import pandas as pd
import simpy
import datetime as dt
import dateutil.tz as tz

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
        except:
            self.start_date = dt.datetime(2020, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

    def resources(self, *args, **kwargs):
        """Define the DES-resources."""
        self.weather_resource = plugins.WeatherResource()

        # Store some abritrary data.
        dates = np.arange(
            dt.datetime(2020, 1, 1), dt.datetime(2020, 2, 1), dt.timedelta(hours=1)
        )
        data = np.sin(np.cumsum(np.ones(len(dates)) * 2 * np.pi / len(dates)))
        d = pd.DataFrame(dict(datetime=dates, hs=data))
        self.weather_resource.store_information(data=d)

    def processes(self, *args, **kwargs):
        """Define DES-processes."""
        self.process = BasicActivity(
            env=self.env,
            registry=self.registry,
            name="example process.",
            duration=3600,
            weather_resource=self.weather_resource,
            limit_expr=lambda hs: hs > 0,
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
        except:
            self.start_date = dt.datetime(2020, 1, 1).replace(tzinfo=tz.UTC)
            self.epoch = self.start_date.timestamp()

        self.env = simpy.Environment(initial_time=self.epoch)
        self.registry = {}

        # Redefine the processes.
        self.processes()

        # Run simulation.
        self.start_simulation()

        return self.project_length()

    def project_length(self, *args, **kwargs):
        """Retrieve the project length."""
        # Extract the event log.
        log = plot.get_log_dataframe(self.process)

        # Find start and stop-dates.
        try:
            start = log["Timestamp"].iloc[0]
            stop = log["Timestamp"].iloc[-1]

            # Return the difference.
            return stop - start
        except Exception:
            pass


# -------------------------------------------------------------------------------------!
class BasicActivity(plugins.HasRequestWindowPluginActivity, model.BasicActivity):
    """BasicActivity with weather plugin."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)
