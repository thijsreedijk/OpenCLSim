''' CONTAINS THE MOST GENERAL AND BASIC OBJECT '''


class SimpyObject:
    '''Python object containing the simpy environment

    General python object, can be inherited by any class requiring a
    simpy simulation environment.

    Parameters
    ----------
    env
        A simpy Environment
    '''

    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env
