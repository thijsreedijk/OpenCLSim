''' CONTAINS SITE CLASS FOR MODELLING THE PORT AND OWF SITES '''
# ----------------------------------------------------------------------------!
import openclsim.core as core
from .appendix import remove_item

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import simpy


# ----------------------------------------------------------------------------!
class Site(core.HasContainer, core.HasResource, core.Identifiable, core.Log):
    ''' Python object used for modelling the involved sites.

    Parameters
    ----------
        capacity: float
            Amount of components the object can hold.
        env: simpy.Environment
            SimPy environment in which the class is created.
        ID: str
            Identification (number) of the object.
        level: float
            Current amount of components in object.
        name: str
            A descriptive name of the object.
        nr_resources: int
            The number of existing resources (berths, cranes, etc.).
    '''

    def __init__(self, env: 'simpy.Environment', capacity: float = 1.00,
                 ID: str = None, level: float = 1.00, name: str = None,
                 nr_resources: int = 1, **kwargs):

        # Instance attributes
        self.__dict__ = remove_item(d=locals(), k='kwargs')
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**remove_item(d=self.__dict__, k='self'))
