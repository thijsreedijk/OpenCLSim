# ----------------------------------------------------------------------------!
import simpy
import openclsim.model as model
from .equipment import InstallationVessel
from .sites import Site
from .appendix import remove_item


# ----------------------------------------------------------------------------!
class MoveActivity(model.MoveActivity):

    ''' Class for modelling the sailing activity of equipment.

    The MoveActivity class takes care of the sailing process,
    and thus movement of an object, when called on.

    Parameters
    ----------
        env: simpy.Environment
            SimPy environment in which object is initialised.
        name: str
            A descriptive name of the activity.
        ID: str
            Identification (number) of the activity, generates by default
            a UUID V4.
        mover: InstallationVessel
            The equipment object to be moved. If the class is initialised
            within an equipment class, 'self' will suffice.
        destination: Site
            Expected destination of the object.
        duration: float
            Time it takes to travel from the current location to the
            destination.
    '''

    def __init__(self, env: simpy.Environment, name: str, destination: Site,
                 mover: InstallationVessel, duration: float, ID: str = None,
                 registry: dict = {}, **kwargs):

        # Instance attributes
        __vars = locals().copy()
        __keys = ['self', 'kwargs', '__class__']
        self.__dict__ = remove_item(d=__vars, k=__keys)
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**self.__dict__)


# ----------------------------------------------------------------------------!
class TransferActivity(model.ShiftAmountActivity):

    ''' Class for modelling the transfer activity of components.

    The TransferActivity class takes care of the transfer of components
    process at a particular site.

    Parameters
    ----------
        env: simpy.Environment
            SimPy environment in which object is initialised.
        name: str
            A descriptive name of the activity.
        ID: str
            Identification (number) of the activity, generates by default
            a UUID V4.
        origin: Site
            The source from which components are transfered.
        destination: Site
            The site to which components are transfered.
        processor: InstallationVessel
            The equipment carrying out the installation activity.
        duration: float
            Time it takes to travel from the current location to the
            destination.
        amount: int
            The maximum number of components installed at once.
    '''

    def __init__(self, env: simpy.Environment, name: str, origin: Site,
                 destination: Site, processor: InstallationVessel,
                 duration: float, amount: int = 1, ID: str = None,
                 registry: dict = {}, **kwargs):

        # Instance attributes
        __vars = locals().copy()
        __keys = ['self', 'kwargs', '__class__']
        self.__dict__ = remove_item(d=__vars, k=__keys)
        self.__dict__.update(**kwargs)

        # Initialise parent classes
        super().__init__(**self.__dict__)
