"""Directory for the weather plugin."""
# -------------------------------------------------------------------------------------!

import datetime as dt
import logging
from inspect import getfullargspec
from typing import Callable

import numpy as np
import pandas as pd

import openclsim.model as model

logger = logging.getLogger(__name__)


class WeatherCriterion:
    """
    Used to add limits to vessels (and therefore acitivities).

    Parameters
    ----------
    condition
        Column of the climate table
    window_length : minutes
        Lenght of the window in minutes
    window_delay : minutes
        Delay of the window compared to the start of the activity
    maximum
        maximal value of the  condition
    minimum
        minimum value of the  condition
    """

    def __init__(
        self,
        name: str,
        condition: str,
        window_length: float,
        maximum: float = None,
        minimum: float = None,
        window_delay: float = 0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.name = name
        self.condition = condition

        try:
            assert (maximum is not None) or (minimum is not None)
            if minimum is not None:
                assert maximum is None
            if maximum is not None:
                assert minimum is None
        except Exception as e:
            raise AssertionError(
                f"One and only one of the parameters minimum or maximum can be defined (error message: {e})."
            )

        self.minimum = minimum
        self.maximum = maximum

        self.window_length = window_length
        self.window_delay = window_delay


class HasWeatherPluginActivity:
    """Mixin forActivity to initialize WeatherPluginActivity."""

    def __init__(self, metocean_criteria, metocean_df, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            metocean_criteria is not None
            and metocean_df is not None
            and isinstance(self, model.PluginActivity)
        ):

            self.metocean_data = metocean_df

            weather_plugin = WeatherPluginActivity(
                weather_criteria=metocean_criteria, metocean_df=self.metocean_data
            )
            self.register_plugin(plugin=weather_plugin, priority=2)


class WeatherPluginActivity(model.AbstractPluginClass):
    """Mixin for MoveActivity to initialize TestPluginMoveActivity."""

    def __init__(self, weather_criteria=None, metocean_df=None):
        assert isinstance(weather_criteria, WeatherCriterion)
        self.weather_criteria = weather_criteria
        self.metocean_df = metocean_df

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        if self.weather_criteria is not None:
            t = float(env.now)
            determined_range = self.check_constraint(start_time=t)

            if not isinstance(determined_range, list):
                raise AssertionError

            elif t < determined_range[0]:
                activity_label = {"type": "plugin", "ref": "waiting on weather"}
                waiting = determined_range[0] - t
                return activity.delay_processing(
                    env, activity_label, activity_log, waiting
                )
            else:
                return {}
        else:
            return {}

    def check_constraint(self, start_time):
        res = self.process_data(self.weather_criteria)
        windows = np.array(res["windows"])
        ts_start = res["dataset_start"]
        ts_stop = res["dataset_stop"]

        filter_windows = windows[windows[:, 1] >= start_time]
        i = 0
        while len(filter_windows) < 1 and i < 10:
            dt = i * (ts_stop - ts_start)
            filter_windows = windows[windows[:, 1] >= start_time - dt]
            i = i + 1

        return list(filter_windows[0])

    def process_data(self, criterion) -> None:

        col = criterion.condition
        orig_data = self.metocean_df.copy()

        # get start and stop date of the data set
        ts_start = min(orig_data["ts"])
        ts_stop = max(orig_data["ts"])

        data = orig_data.copy()
        data["ts"] = data["ts"]
        data["cur"] = True
        data["prev_ts"] = data.ts.shift(1)

        if criterion.maximum is not None:
            threshold = {col: criterion.maximum}

            if orig_data[col].max() < threshold[col]:
                threshold[col] = orig_data[col].max() - 0.0001

            data["cur"] = data["cur"] & (data[col] <= threshold[col])
            data[f"{col}_prev"] = data[col].shift(1)

            data[f"{col}_inter"] = data["ts"]
        else:
            threshold = {col: criterion.minimum}

            if orig_data[col].min() > threshold[col]:
                threshold[col] = orig_data[col].min() + 0.0001

            data["cur"] = data["cur"] & (data[col] >= threshold[col])
            data[f"{col}_prev"] = data[col].shift(1)
            data[f"{col}_inter"] = data["ts"]

        data["prev"] = data.cur.shift(1)
        data = data[1:]
        data = data[data.cur ^ data.prev]
        data["type"] = "start"

        data[f"{col}_inter"] = data.ts
        data2 = data.loc[(data[col] - data[f"{col}_prev"]) != 0]
        data2[f"{col}_inter"] = data2.prev_ts + (data2.ts - data2.prev_ts) * (
            threshold[col] - data2[f"{col}_prev"]
        ) / (data2[col] - data2[f"{col}_prev"])
        if criterion.maximum is not None:
            data.loc[data[col] > threshold[col], "type"] = "end"
        else:
            data.loc[data[col] < threshold[col], "type"] = "end"

        columns = [f"{col}_inter"]
        data["ts_inter"] = np.maximum.reduce(data[columns].values, axis=1)
        data["end_inter"] = data.ts_inter.shift(-1)

        if data.iloc[0]["type"] == "end":
            data.iloc[0, data.columns.get_loc("type")] = "start"
            data.iloc[0, data.columns.get_loc("end_inter")] = data.iloc[0]["ts_inter"]
            data.iloc[0, data.columns.get_loc("ts_inter")] = orig_data.iloc[0]["ts"]
        if data.iloc[-1]["type"] == "start":
            data.iloc[-1, data.columns.get_loc("end_inter")] = orig_data.iloc[-1]["ts"]

        data.rename(columns={"ts_inter": "start_inter"}, inplace=True)

        data = data[data["type"] == "start"][["start_inter", "end_inter"]]

        data = data[data["end_inter"] - data["start_inter"] > criterion.window_length]
        data["end_inter"] = (
            data["end_inter"] - criterion.window_length - criterion.window_delay
        )
        data["start_inter"] = data["start_inter"] - criterion.window_delay
        windows = [list(data.iloc[d]) for d in range(len(data))]

        result = {
            "dataset_start": ts_start,
            "dataset_stop": ts_stop,
            "windows": windows,
        }
        return result


# -------------------------------------------------------------------------------------!
class HasOperationalLimits(object):
    """Impose operational limits on a process."""

    def __init__(self, weather_resource=None, limit_expr=None, *args, **kwargs) -> None:
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Assess if weather_resource is instance of WeatherResource.
        assert isinstance(
            weather_resource, WeatherResource
        ), "weather_resource should be an instance of WeatherResource"

        # Assign weather resource to activity.
        self.weather_resource = weather_resource

        # Add activity to database of weather resource.
        if self.name not in weather_resource.activity_database.keys():
            self.weather_resource.store_activity(id=self.name, limit_expr=limit_expr)


# -------------------------------------------------------------------------------------!
class HasRequestWindowPluginActivity(HasOperationalLimits):
    """Add a request window pre-process to a process."""

    def __init__(self, *args, **kwargs) -> None:
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Assess if plugin was properly called.
        assert isinstance(
            self, model.PluginActivity
        ), "Plugin was unable to initialise."

        # Define the activity.
        plugin = RequestWindowPluginActivity(weather_resource=self.weather_resource)

        # Register the plugin activity.
        self.register_plugin(plugin=plugin, priority=2)


# -------------------------------------------------------------------------------------!
class RequestWindowPluginActivity(model.AbstractPluginClass):
    """Processes the request window pre-process."""

    def __init__(self, weather_resource, *args, **kwargs) -> None:
        """Class constructor."""
        super().__init__(*args, **kwargs)

        self.weather_resource = weather_resource

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        """Apply the activity prior to the actual activity."""
        # Find the required delay.
        activity_delay = self.weather_resource.next_suitable_window(
            env=env, id=activity.name, window_length=activity.duration
        )

        activity_label = {"type": "plugin", "ref": "waiting on weather"}

        return activity.delay_processing(
            env, activity_label, activity_log, activity_delay
        )


# -------------------------------------------------------------------------------------!
class WeatherResource(object):
    """Build a database with the relevant data."""

    def __init__(self, *args, **kwargs) -> None:
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Setup databases.
        self.activity_database = {}
        self.conditions_database = pd.DataFrame(columns=["Timestamp"])

    def binary_sequence_generator(self, limit_expr: Callable) -> pd.DataFrame:
        """Transform time-series into workability states."""
        # Make sure limit_expr is a python function.
        assert isinstance(limit_expr, Callable), "limit_expr is not a python function."

        # Create a temporary copy of the conditions database.
        df = self.conditions_database.copy()

        # Determine the limit state function parameters.
        vars_ = getfullargspec(limit_expr)[0]

        # Remove `self` if it's in the variables.
        if "self" in vars_:
            vars_.remove("self")

        # Assess if the variables are in the database.
        assert set(vars_) <= set(
            df.columns
        ), "Parameter(s): {0} of limit expression is/are not in dataset.".format(
            set(vars_) - set(df.columns)
        )

        # Find the binary sequence.
        df["violated"] = limit_expr(*[df[var] for var in vars_])

        # Return new dataset.
        return df

    def compute_windows(self, d: pd.DataFrame) -> pd.DataFrame:
        """Compute weather windows using a weather window analysis."""
        # Assess if `d` is a pandas dataframe.
        assert isinstance(d, pd.DataFrame), "`d` must be a pandas.DataFrame"

        # Assess if timestamps in columns of dataframe.
        assert "Timestamp" in d.columns, "'Timestamp' not in columns of `d`."

        # Assess if violated in columns of dataframe.
        assert "violated" in d.columns, "'violated' not in columns of `d`."

        # Find consecutive blocks.
        d["block"] = (d["violated"].shift(1) != d["violated"]).cumsum()

        # Derive the windows.
        blocks = pd.DataFrame(
            dict(
                start_date=d.groupby("block")["Timestamp"].first(),
                stop_date=d.groupby("block")["Timestamp"].last(),
                violated=d.groupby("block")["violated"].first(),
            )
        )

        # Fill the latest stop date by the end date of the record.
        # blocks.loc[len(blocks) - 1, "stop_date"] = d["Timestamp"].iloc[-1]

        # Determine the blocks' length.
        blocks["length"] = blocks["stop_date"] - blocks["start_date"]

        # Return weather windows.
        return blocks

    def store_activity(self, id, limit_expr, *args, **kwargs):
        """Store OpenCLSim activity in database."""
        # Perform the weather window analysis.
        binary_sequence = self.binary_sequence_generator(limit_expr=limit_expr)
        windows = self.compute_windows(d=binary_sequence)

        # Store the activity and its windows in database.
        self.activity_database[str(id)] = dict(windows=windows)

    def store_information(self, data: pd.DataFrame = None, *args, **kwargs):
        """
        Store information in the conditions database.

        Stores relevant data in the database. Requires the data-argument
        to be a pandas.DataFrame that has at least a `datetime` column.
        """
        # Assert if datetime in columns.
        assert "datetime" in data.columns, "Could not find datetime column in data."

        # If the database is empty, append the data.
        if len(self.conditions_database) == 0:
            self.conditions_database = data.rename(dict(datetime="Timestamp"), axis=1)

        elif len(self.conditions_database != 0):
            data = data.rename(dict(datetime="Timestamp"), axis=1)

            self.conditions_database = pd.merge(
                left=self.conditions_database, right=data, on="Timestamp", how="outer"
            ).sort_values("Timestamp")

    def next_suitable_window(self, env, id, window_length, *args, **kwargs):
        """Query database for the next suitable weather window."""
        # Find windows from database.
        windows = self.activity_database[id]["windows"]

        # Find the first workable weather window
        try:

            # Assess if currently there is a workable window.
            current_window = windows.loc[
                (windows["start_date"] <= dt.datetime.utcfromtimestamp(env.now))
                & (dt.datetime.utcfromtimestamp(env.now) < windows["stop_date"])
            ]

            current_window_length = (
                (current_window["stop_date"] - dt.datetime.utcfromtimestamp(env.now))
                .dt.total_seconds()
                .iloc[0]
            )

            if (current_window_length >= window_length) & (
                ~current_window["violated"].iloc[0]
            ):
                delay_by = 0

            # otherwise search for the next available window.
            else:
                first = windows.loc[
                    (~windows["violated"])
                    & (windows["start_date"] > dt.datetime.utcfromtimestamp(env.now))
                    & (windows["length"].dt.total_seconds() >= window_length)
                ].iloc[0]

                delay_by = first.start_date.timestamp() - env.now

            return delay_by

        except IndexError as e:

            logger.debug(
                msg=(
                    "\n"
                    + "-" * 72
                    + "\n"
                    + "The waiting on weather event has been skipped because:\n"
                    + "    (1) the dataset did not provide any sufficient window.\n"
                    + "    (2) the dataset is to short.\n"
                    + "Consider lowering the activity duration to test if runs properly.\n"
                    + "-" * 72
                    + "\n"
                ),
                exc_info=e,
            )
            return 0

        # Any other error will be resolved by returning no delay.
        except Exception as e:
            logger.debug(
                msg=(
                    "The waiting on weather event has been skipped for unknown reasons.\n"
                ),
                exc_info=e,
            )
            return 0
