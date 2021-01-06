import openclsim.core as core
import simpy
import shapely
from typing import Callable
from .appendix import remove_item


# ----------------------------------------------------------------------------!
class InstallationVessel(core.Identifiable, core.Log,
                         core.ContainerDependentMovable, core.Processor,
                         core.HasResource):

    ''' Class for modelling installation equipment.

    Most general class of an installation vessel. User may use the
    class to describe any generic equipment, however, it is recommended
    to use the class as base class for other more equipment specific
    classes.

    Parameters
    ----------
        env: simpy.Environment
            SimPy environment in which object is initialised.
        name: str
            A descriptive name of the object.
        ID: str
            Identification (number) of the object, generates by default
            a UUID V4.
        compute_v: function
            Python function returning the cruising velocity for a given
            load.
        geometry: shapely.geometry.Point
            Current location of the object.
        capacity: float
            Amount of components allowed on deck of vessel. By default
            1.00.
        level: float
            Current number of components stored on deck. By default 0.00.
        nr_resources: int
            Number of available resources. By default 1.00.
    '''

    def __init__(self, env: simpy.Environment, name: str,
                 geometry: shapely.geometry.Point, ID: str = None,
                 capacity: float = 1.00, level: float = 1.00,
                 nr_resources: int = 1, compute_v: Callable = None,
                 **kwargs):

        # Instance attributes
        __vars = locals().copy()
        __keys = ['self', 'kwargs', '__class__']
        self.__dict__ = remove_item(d=__vars, k=__keys)
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**self.__dict__)
