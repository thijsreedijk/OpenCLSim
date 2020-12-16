'''' CONTAINS ADDITIONAL, POSSIBLY HELPFUL PYTHON FUNCTIONS. '''
# ----------------------------------------------------------------------------!


def remove_item(d: dict, k: str):
    '''Python function removing a key, value pair from a dictionary

    Parameters
    ----------
        d: dict
            Dictionary from which the pair should be removed.
        k: str
            Key indicating which pair should be removed.

    Returns
    -------
        new_dict: dict
            A python dictionary without the previously removed item.
    '''

    return dict([(key, value) for key, value in d.items() if key != k])
