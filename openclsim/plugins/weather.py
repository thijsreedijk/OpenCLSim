"""Directory for the weather plugin."""

import os
from datetime import datetime as dt
from typing import Callable

import numpy as np
import pandas as pd
import simpy

import openclsim.model as model


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
        """Class constructor."""
        super().__init__(*args, **kwargs)

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
                "One and only one of the parameters minimum or maximum can be defined"
                + f"(error message: {e})."
            )

        self.minimum = minimum
        self.maximum = maximum

        self.window_length = window_length
        self.window_delay = window_delay


class HasWeatherPluginActivity:
    """Mixin forActivity to initialize WeatherPluginActivity."""

    def __init__(self, metocean_criteria, metocean_df, *args, **kwargs):
        """Class constructor."""
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
        """Class constructor."""
        assert isinstance(weather_criteria, WeatherCriterion)
        self.weather_criteria = weather_criteria
        self.metocean_df = metocean_df

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        """Pre-processor."""
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
        """Check for constraints."""
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
        """Derive weather windows."""
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
    """
    Provide operational constraints to an activity or equipment.

    The HasOperationLimits class allows the user to set operational
    limits to an activity or equipment. Though, the class is mainly
    setup to be inherited from by other classes, such as the
    `HasRequestWindowPluginActivity` (see below).

    Parameters
    ----------
        limit_expr: Callable
            A (Python) function expressing the operational limits in
            terms of critical parameters, for example, the significant
            wave height and peak wave period `f(hs, tp)`. The function
            should return a bool, where `True` is considered as the
            event in which the limit has been exceeded.

    """

    def __init__(self, limit_expr: Callable, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Instance attributes
        self.limit_expr = limit_expr


# -------------------------------------------------------------------------------------!
class HasRequestWindowPluginActivity(HasOperationalLimits):
    """
    Initialise the RequestWindowPluginActivity.

    An `HasRequestWindowPluginActivity` instance initialises the waiting
    on weather activity which is modelled using the
    `RequestWindowPluginActivity`. For examples please refer to the
    corresponding notebooks.

    Parameters
    ----------
        offshore_environment: OffshoreEnvironment
            An instance of the OffshoreEnvironment class (see below).
    """

    def __init__(
        self, offshore_environment: "OffshoreEnvironment" = None, *args, **kwargs
    ):
        """Class constructor."""
        super().__init__(*args, **kwargs)

        if isinstance(self, model.PluginActivity) and isinstance(
            offshore_environment, OffshoreEnvironment
        ):
            plugin = RequestWindowPluginActivity(
                offshore_environment=offshore_environment
            )
            self.register_plugin(plugin=plugin, priority=2)


# -------------------------------------------------------------------------------------!
class RequestWindowPluginActivity(model.AbstractPluginClass):
    """
    Models the activity of a waiting on weather event.

    The RequestWindowPluginActivity class is used to model the activity
    of a waiting on weather event.

    Parameters
    ----------
        offshore_environment: OffshorEnvironment
            An instance of the OffshoreEnvironment class (see below).

    """

    def __init__(self, offshore_environment: "OffshoreEnvironment", *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Instance attributes
        self.oe = offshore_environment

    def pre_process(self, env, activity_log, activity, *args, **kwargs):
        """
        Apply the waiting on weather event.

        The `pre_process` function applies the waiting on weather event
        ahead of the `main` activity.

        """
        activity_delay = self.oe.find_window(
            env=env, limit_expr=activity.limit_expr, duration=activity.duration
        )

        activity_label = {"type": "plugin", "ref": "waiting on weather"}

        return activity.delay_processing(
            env, activity_label, activity_log, activity_delay
        )


# -------------------------------------------------------------------------------------!
class OffshoreEnvironment(object):
    """
    Holds information about the offshore environment.

    An instance of the OffshoreEnvironment class holds information of
    site specific data. Besides, the class has a certain `find_window`
    method which searches for the first workable weather window for a
    given activity.

    """

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)

    def store_information(
        self, var: str = None, value=None, filename: str = None, **kwargs
    ):
        """
        Store metocean information in the dataset.

        The store_information function provides the user a method to
        pass information to the dataset about site specific metocean
        conditions. The function takes either a single value using the
        `value` argument, or a series of values from a `.csv` file. The
        latter requires two columns of data: (1) timestamps from when
        the data was recorded and (2) the corresponding values. Besides,
        the first row of the file is processed as column names.

        If a filename is provided, the pandas package is used to read
        the contents. For that reason, it is possible to manipulate the
        reading process using keyword-arguments. Please refer to the
        `pandas.read_csv` documentation.

        Parameters
        ----------
            var: str
                Variable name as a single word or abbriviation.
            value: str
                Value of the corresponding variable.
            filename: str
                Path to the `.csv` file.

        Examples
        --------
            >>> import openclsim.plugins as plugins
            >>> oe = plugins.OffshoreEnvironment()
            >>> # Store a dataset from a *.csv file.
            >>> oe.store_information(var="hs", filename="./file.csv")
            >>> # Or store information about, e.g., the sites ID.
            >>> oe.store_information(var="id", value="Offshore Site ID")

        """
        # Test if a variable name is (properly) provided.
        if (var is not None) and (isinstance(var, str) is False):
            raise ValueError("The `var` argument accepts only a `string` type.")
        elif var is None:
            raise TypeError(
                "`store_information` requires at least the positional arguments: `var`"
                + " and `value` or `filename`."
            )
        else:
            pass

        # Test if a value or filename is (properly) provided.
        if (value is None) and (filename is None):
            raise TypeError(
                "`store_information` requires at least one of the positional arguments:"
                + " `value` or `filename` to be set."
            )
        elif (value is not None) and (filename is not None):
            raise TypeError(
                "`store_information accepts either a `value` or `filename` to be set."
            )
        elif (filename is not None) and (isinstance(filename, str) is False):
            raise ValueError("The `filename` argument accepts only a `string` type.")
        elif (filename is not None) and (os.path.isfile(filename) is False):
            raise FileNotFoundError(f"Unable to find the file: `{filename}`.")
        elif (filename is not None) and (len(filename) == 0):
            raise ValueError("The `filename` argument received an empty `string`.")
        else:
            pass

        # Try to store the information as an instance attribute.
        if (value is not None) and (filename is None):
            try:
                self.__dict__[var] = value
            except Exception:
                raise Exception("For some reason I'm unable to store the information.")

        # Try to store the data in a pandas dataframe.
        elif (value is None) and (filename is not None) and (os.path.isfile(filename)):

            # Read and import file.
            try:
                dataframe = pd.read_csv(filename, **kwargs)
            except Exception:
                raise Exception("Unable to read `.csv` properly.")

            # Parse dates to datetime.datetime objects.
            try:
                dataframe.iloc[:, 0] = pd.to_datetime(dataframe.iloc[:, 0])
            except Exception:
                raise Exception(
                    "Unable to parse the timestamps to datetime.datetime objects. "
                    + "Make sure the format is either:\n `dd-mm-yy hh:mm:ss` or\n "
                    + "`dd/mm/yy hh:mm:ss`"
                ) from None

            # Parse possible string values to numeric.
            try:
                dataframe.iloc[:, 1] = pd.to_numeric(
                    dataframe.iloc[:, 1], errors="coerce"
                )
            except Exception:
                raise Exception(
                    "For some reason I'm unable to transform values to numeric values."
                )

            # Set dates as index
            try:
                columns = dataframe.columns
                dataframe = dataframe.set_index(columns[0])
            except Exception:
                raise Exception("For some reason I'm Unable to set the date as index.")

            # Store dataframe as instance attribute
            self.__dict__[var] = dataframe

        else:
            pass

    def find_window(
        self, env: simpy.Environment, limit_expr: Callable, duration: float, **kwargs
    ):
        """
        Find the next workable weather window.

        The `find_window` function searches for the first workable
        weather window present in a given dataset. It requires the
        operational limits, the simulation environment and data about
        the offshore environment. It will raise an error message if
        these are not properly initialised using the
        `OffshoreEnvironment` class. For examples, please refer to the
        corresponding notebooks.

        Parameters
        ----------
            env: simpy.Environment
                A SimPy simulation environment.
            limit_expr: Callable
                A (Python) function expressing the operational limits
                in terms of critical parameters, for example, the
                significant wave height and peak wave period
                `f(hs, tp)`. The function should return a bool, where
                `True` is considered as the event in which the limit
                has been exceeded.

        """
        # Find which parameters are of interest.
        vars = list(limit_expr.__code__.co_varnames)

        # Test if they are allocated within the attributes.
        try:
            series = [self.__dict__[var] for var in vars]

        except KeyError:
            raise KeyError(
                "`limit_expr` uses arguments that are not present in the database."
            ) from None

        # Join the data into a single dataframe
        try:
            dataframe = pd.concat(series, axis="columns")
            dataframe.columns = vars
        except Exception:
            raise Exception("Unable to merge the constraining variables.")

        # Test if the limit is exceeded, True indicates it is.
        dataframe["limit_exceeded"] = limit_expr(*[dataframe[var] for var in vars])

        # Create consecutive time `blocks`.
        dataframe["block"] = (
            dataframe["limit_exceeded"].shift(1) != dataframe["limit_exceeded"]
        ).cumsum()

        # Rename the index.
        try:
            dataframe.index.names = ["date"]
        except Exception:
            raise Exception("For some reason unable to rename the index.")

        # Create a dataframe of consecutive time `blocks`.
        blocks = pd.DataFrame(
            {
                "start_date": dataframe.reset_index().groupby("block").date.first(),
                "end_date": (
                    dataframe.reset_index().groupby("block").date.first().shift(-1)
                ),
                "limit_exceeded": (
                    dataframe.reset_index().groupby("block").limit_exceeded.first()
                ),
            }
        )

        # Derive the blocks length
        blocks["length"] = (
            blocks["end_date"] - blocks["start_date"]
        ).dt.total_seconds()

        # Find the first workable window and return the delay.
        try:
            next = blocks[
                (blocks["length"] >= duration)
                & (~blocks["limit_exceeded"])
                & (blocks["start_date"] >= dt.utcfromtimestamp(env.now))
            ].iloc[0]

            delay_by = next.start_date.timestamp() - env.now

            return delay_by

        # It might be that our data is out of range.
        except IndexError:
            print("-" * 72)
            print("The waiting on weather event has been skipped because:\n")
            print("    (1) the dataset did not provide any sufficient window.\n")
            print("    (2) the dataset is to short.\n")
            print("Consider lowering the activity duration to see if it works.")
            print("-" * 72)
            return 0

        # Any other error will be resolved by returning no delay.
        except Exception:
            print(
                "The waiting on weather event has been skipped for unknown reasons.\n"
            )
            return 0
