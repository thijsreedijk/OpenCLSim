import logging
from functools import reduce
from multiprocessing import Pool, cpu_count

import numpy as np
import pandas as pd
import tqdm.notebook as tqdm
import xarray as xr


# -------------------------------------------------------------------------------------!
def reset_direction(dataframe, dir_col="dir"):
    """Reset the wave angle to a [0, 360] range."""
    dataframe[dir_col] = dataframe[dir_col] % 360
    return dataframe


def pandas_to_xarray(dataframe):
    """Converts a pandas multi-index dataframe into a 3D xarray."""
    # Simplify variable name.
    df = dataframe

    # Define columns of interest.
    DOFs = [
        "RAOSurgeAmp",
        "RAOSurgePhase",
        "RAOSwayAmp",
        "RAOSwayPhase",
        "RAOHeaveAmp",
        "RAOHeavePhase",
        "RAORollAmp",
        "RAORollPhase",
        "RAOPitchAmp",
        "RAOPitchPhase",
        "RAOYawAmp",
        "RAOYawPhase",
    ]

    # Separate dataframe by degree of freedom.
    dfs = [df[DOF] for DOF in DOFs]

    # Create xarray.DataArray
    da = xr.DataArray(
        data=dfs,
        dims=["DOF", "freq", "dir"],
        coords={"DOF": DOFs, "freq": dfs[0].index.values, "dir": dfs[0].columns.values},
    )

    return da


# Define a parallelise function.
def apply_parallelise(groups, func, column):
    """Apply a function parallel to pandas.GroupBy groups."""
    series = (group[column] for name, group in groups)
    results = []

    with Pool(processes=cpu_count()) as p:
        with tqdm(total=len(groups)) as pbar:
            for i, res in enumerate(p.imap(func, series)):
                pbar.update()
                results.append(res)

    results = pd.DataFrame(
        index=pd.MultiIndex.from_tuples(groups.groups.keys()), data=dict(values=results)
    )

    return results


# Append the 0 [deg] angle and rename to 360 [deg].
def append_angle(da: xr.DataArray = None):
    return xr.concat(
        [da, da.sel(dict(dir=0)).assign_coords(dict(dir=360.0))], dim="dir"
    )


# -------------------------------------------------------------------------------------!
def get_event_log(activity_list: list, entities: list = None):
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

    # Read the state of the entities
    try:
        entity_logs = [
            (
                pd.DataFrame(entity.log)[["Timestamp", "ActivityState", "ObjectState"]]
            ).rename(columns={"ObjectState": entity.name})
            for entity in entities
        ]

        merged_log = (
            reduce(
                lambda left, right: pd.merge(
                    left=left,
                    right=right,
                    how="outer",
                    left_on=["Timestamp", "ActivityState"],
                    right_on=["Timestamp", "ActivityState"],
                ),
                [event_log, *entity_logs],
            )
            .fillna(method="ffill")
            .fillna(method="bfill")
        )

        return merged_log

    except ValueError:
        logging.warning("Could not merge the logs of entities and activities.")

    except Exception:
        logging.debug("Entities were not read.")

    return event_log


# -------------------------------------------------------------------------------------!
def resultant_vector(x1, x2, theta1, theta2):

    # Degrees to radians.
    theta1, theta2 = (np.degrees(theta1), np.degrees(theta2))

    # Vector elements.
    X1 = np.array([x1 * np.cos(theta1), x1 * np.sin(theta1)])
    X2 = np.array([x2 * np.cos(theta2), x2 * np.sin(theta2)])

    # Resultant vector.
    X = X1 + X2

    # Return magnitude
    return np.sqrt((X.T ** 2).sum(axis=1))
