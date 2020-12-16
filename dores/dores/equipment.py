''' CONTAINS CLASSES TO DESCRIBE THE EQUIPMENT INVOLVED DURING THE PROCESS '''
# ----------------------------------------------------------------------------!
import openclsim.core as core
from .appendix import remove_item

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import simpy
    import shapely.geometry.Point


# ----------------------------------------------------------------------------!
class InstallationVessel(core.Movable, core.HasContainer,
                         core.HasResource, core.Identifiable, core.Log,
                         core.Processor):
    ''' Python object for modelling the installation equipment.

    Most general class of an installation vessel. User may use the
    class to describe any generic equipment, however, it is recommended
    to use the class as base class for other more equipment specific
    classes.

    Parameters
    ----------
        capacity: float
            Amount of components the object can hold.
        env: simpy.Environment
            SimPy environment in which the class is created.
        geometry: shapely.geometry.Point
            The current location of the object in [lon, lat].
        ID: str
            Identification (number) of the object.
        level: float
            Current amount of components in object.
        name: str
            A descriptive name of the object.
        v: float
            Cruising speed of a vessel or equipment.
    '''

    def __init__(self, env: 'simpy.Environment',
                 geometry: 'shapely.geometry.Point', capacity: float = 1.00,
                 ID: str = None, level: float = 1.00, name: str = None,
                 nr_resources: int = 1, v: float = None, **kwargs):

        # Instance attributes
        self.__dict__ = remove_item(d=locals(), k='kwargs')
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**remove_item(d=self.__dict__, k='self'))

