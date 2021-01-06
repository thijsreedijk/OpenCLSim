# ----------------------------------------------------------------------------!
import openclsim.core as core
import simpy
import shapely
from . import remove_item


# ----------------------------------------------------------------------------!
class Site(core.Identifiable, core.Log, core.Locatable, core.HasContainer,
           core.HasResource):

    ''' Class for modelling a construction site or transport hub.

    Python object containing information of a certain site. This may be
    a port or the offshore site.

    Parameters
    ----------
        env: simpy.Environment
            SimPy environment in which object is initialised.
        name: str
            A descriptive name of the object.
        ID: str
            Identification (number) of the object, generates by default
            a UUID V4.
        geometry: shapely.geometry.Point
            Location of the site in lon, lat coordinates.
        capacity: float
            Amount of components the object (site) can hold. By default
            1.00.
        level: float
            Amount of components currently on site. By default 1.00.
        nr_resources: int
            Number of available resources, these may be berths, cranes,
            etc. By default 1.
    '''
    def __init__(self, env: simpy.Environment, name: str,
                 geometry: shapely.geometry.Point, ID: str = None,
                 capacity: float = 1.00, level: float = 1.00,
                 nr_resources: int = 1, **kwargs):

        # Instance attributes
        __vars = locals().copy()
        __keys = ['self', 'kwargs', '__class__']
        self.__dict__ = remove_item(d=__vars, k=__keys)
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**self.__dict__)
