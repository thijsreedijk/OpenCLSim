"""Contains a number of extra functions."""
# -------------------------------------------------------------------------------------!
from collections.abc import Iterable
import pandas as pd


# -------------------------------------------------------------------------------------!
def remove_item(d: dict, k: str or list):
    """
    Remove key, value pair from dictionary.

    Python function for removing a (key, value) pair from a dictionary.
    One or multiple keys may be provided using either a single string
    or a list of strings.

    Parameters
    ----------
        d: dict
            Dictionary from which the pair should be removed.
        k: str or list
            Key indicating which pair should be removed.

    Returns
    -------
        new_dict: dict
            A python dictionary without the previously removed item.

    """
    if type(k) is str:
        return dict([(key, value) for key, value in d.items() if key != k])

    elif type(k) is list:
        return dict([(key, value) for key, value in d.items() if key not in k])


# -------------------------------------------------------------------------------------!
def get_event_log(activity_list: list):
    """
    Return the event log of the installation process.

    The get_event_log function takes a list containing the
    basic activities involved during the installation process.
    Using some basic operation it concatenates the logs of the given
    activities.

    Parameters
    ----------
        activity_list: list
            A list containing the basic activities defined in the
            simulation environment.

    Returns
    -------
        event_log: pandas.DataFrame
            A pandas dataframe object with the corresponding event log.

    """
    # Combine activity logs
    dataframe = pd.concat([pd.DataFrame(x.log) for x in activity_list])
    dataframe["NumericState"] = dataframe["ActivityState"] == "START"
    dataframe = dataframe.sort_values(by=["Timestamp", "NumericState"])

    # Add descriptions
    id_map = {act.id: act.name for act in activity_list}

    dataframe["Description"] = dataframe["ActivityID"]
    dataframe["Description"] = dataframe["Description"].replace(id_map)

    event_log = dataframe[["Timestamp", "ActivityState", "Description", "ActivityID"]]

    return event_log


# -------------------------------------------------------------------------------------!
def flatten(lst: list):
    """
    Flatten a multi-level nested list.

    The flatten function takes any arbitrary nested list and flattens
    it. The function returns a Python generator object, therefore, use
    the function in combination with Pythons' list() function to unpack
    the values.

    Paramters
    ---------
        lst: list
            A multi-level nested list.

    Example
    -------
        >>> list(flatten(['A', 'B', ['C', ['D'], 'E'], 'F']))
        >>> ['A', 'B', 'C', 'D', 'E', 'F']
    """
    for item in lst:
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            yield from flatten(item)
        else:
            yield item
