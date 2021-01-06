# ----------------------------------------------------------------------------!
import pandas as pd


# ----------------------------------------------------------------------------!
def remove_item(d: dict, k: str or list):
    '''Python function removing a key, value pair from a dictionary
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
    '''

    if type(k) is str:
        return dict([(key, value) for key, value in d.items() if key != k])

    elif type(k) is list:

        for k in k:
            d = dict([(key, value) for key, value in d.items() if key != k])

        return d


# ----------------------------------------------------------------------------!
def get_event_log(activity_list: list):
    ''' Function returning the event log of the installation process.
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
    '''

    # Combine activity logs
    dataframe = pd.concat([pd.DataFrame(x.log) for x in activity_list])
    dataframe['NumericState'] = (dataframe['ActivityState'] == 'START')
    dataframe = dataframe.sort_values(by=['Timestamp', 'NumericState'])

    # Add descriptions
    id_map = {act.id: act.name for act in activity_list}

    dataframe['Description'] = dataframe['ActivityID']
    dataframe['Description'] = dataframe['Description'].replace(id_map)

    event_log = dataframe[['Timestamp', 'ActivityState', 'Description',
                           'ActivityID']]

    return event_log
