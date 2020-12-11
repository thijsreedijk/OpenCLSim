''' FILE CONTAINING A NUMBER OF USEFUL PYTHON FUNCTIONS '''
# ----------------------------------------------------------------------------!
import scipy.stats as st
import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------!
def lognorm(mean, std):
    mu = np.log(mean ** 2 / np.sqrt(mean ** 2 + std ** 2))
    sigma = np.sqrt(np.log(1 + std ** 2 / mean ** 2))
    return st.lognorm(s=sigma, scale=np.exp(mu))


# ----------------------------------------------------------------------------!
def import_data(fname, **kwargs):

    # Import data
    try:
        database = pd.read_csv(fname, delimiter=';', **kwargs)
        if (len(database.columns) != 3):
            raise Exception('Was unable to separate columns properly')

    except Exception:
        try:
            database = pd.read_csv(fname, delimiter=',', **kwargs)
            if (len(database.columns) != 3):
                raise Exception('Was unable to separate columns properly')
        except Exception:
            raise Exception(
                'Couldnt separate columns properly, check delimiter'
            )

    # Check if column names are correct
    required = ['DATE', 'TIME', 'VALUE']
    cols = database.columns
    assert (all(x in cols for x in required)), (
        '.csv file should have headers: DATE, TIME, VALUE'
    )

    # Turn strings into floats
    database['VALUE'] = pd.to_numeric(database['VALUE'],
                                      errors='coerce')

    # Turn no data into Numpy's NaN value
    mask = database['VALUE'] > 10000
    database['VALUE'][mask] = np.nan

    # Merge date and time strings into datetime object
    date = database['DATE']
    time = database['TIME']
    merged = date + ' ' + time

    try:
        database['DATETIME'] = pd.to_datetime(
            merged,
            format='%d-%m-%Y %H:%M:%S'
        )
    except Exception:
        try:
            database['DATETIME'] = pd.to_datetime(
                merged,
                format='%d/%m/%Y %H:%M:%S'
            )
        except Exception:
            raise Exception('Unable to match timestamp format')

    return database[['DATETIME', 'VALUE']]
