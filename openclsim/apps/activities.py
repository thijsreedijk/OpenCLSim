"""Provide a number of typical activity classes."""
# -------------------------------------------------------------------------------------!
import openclsim.model as model
import openclsim.plugins as plugins


# -------------------------------------------------------------------------------------!
class Transit(plugins.HasRequestWindowPluginActivity, model.MoveActivity):
    """
    Model the sailing activity.

    The `Transit` class allows the user to quickly adapt the OpenCLSim
    approach for modelling a move activity. Specifying the
    `offshore_environment` and `limit_expr` sets operational limits to 
    the process.

    Parameters
    ----------
        env: simpy.Environment
            A SimPy simulation environment.
        registry: dict
            A dictionary in which the activities are stored.
        name: str
            A descriptive name for storing the activity in the log.
        duration: float
            Length of the activity.
        mover: apps.InstallationEquipment
            The equipment being displaced.
        destination: apps.Site
            The destination to which the equipment is moved.
        offshore_environment: plugins.OffshoreEnvironment
            An instance of the offshore environment.
        limit_expr: Callable
            A (Python) function expressing the operational limits in
            terms of critical parameters, for example, the significant
            wave height and peak wave period `f(hs, tp)`. The function
            should return a bool, where `True` is considered as the
            event in which the limit has been exceeded. By default set
            to None, therefore skipping the limits.
    """

    def __init__(self, *args, **kwargs):
        """Construct object."""
        super().__init__(*args, **kwargs)


# -------------------------------------------------------------------------------------!
class TransferObject(plugins.HasRequestWindowPluginActivity, model.ShiftAmountActivity):
    """
    Model the (un)loading process from vessel to site and vice versa.

    The `TransferObject` class allows the user to quickly adapt the
    OpenCLSim approach for modelling a shift/transfer activity in which
    objects are shifted from a carrier to a site and vice versa.
    Specifying the `offshore_environment` and `limit_expr` sets
    operational limits to the process.

    Parameters
    ----------
        env: simpy.Environment
            A SimPy simulation environment.
        registry: dict
            A dictionary in which the activities are stored.
        name: str
            A descriptive name for storing the activity in the log.
        duration: float
            Length of the activity.
        processor: apps.InstallationEquipment
            The equipment processing the transfer.
        origin: apps.Site or apps.InstallationEquipment
            The stock from which objects are transferred.
        destination: apps.Site or apps.InstallationEquipment
            The location to which the objects are transferred.
        amount: float
            The number of objects to transfer. By default 1.00.
        offshore_environment: plugins.OffshoreEnvironment
            An instance of the offshore environment.
        limit_expr: Callable
            A (Python) function expressing the operational limits in
            terms of critical parameters, for example, the significant
            wave height and peak wave period `f(hs, tp)`. The function
            should return a bool, where `True` is considered as the
            event in which the limit has been exceeded. By default set
            to None, therefore skipping the limits.
    """

    def __init__(self, amount: float = 1, *args, **kwargs):
        """Construct object."""
        super().__init__(amount=amount, *args, **kwargs)
