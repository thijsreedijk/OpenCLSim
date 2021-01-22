"""Provide base class for equipment."""
# -------------------------------------------------------------------------------------!
import openclsim.core as core


# -------------------------------------------------------------------------------------!
class InstallationEquipment(
    core.Identifiable,
    core.Log,
    core.ContainerDependentMovable,
    core.Processor,
    core.HasResource,
    core.HasContainer,
    core.LoadingFunction,
    core.UnloadingFunction,
):
    """
    Provide a base class for equipment.

    The `InstallationEquipment` class provides a basic example on how
    to use the OpenCLSim to model installation equipment.

    Parameters
    ----------
        env: simpy.Environment
            A SimPy simulation environment.
        registry: dict
            An empty python dictionary.
        name: str
            A name to identify the vessel with.
        geometry: shapely.geometry.Point
            The current location in geojson format. Preferably by
            providing a `shapely.geometry.Point` object.
        capacity: int
            The maximum amount of objects that may be stored on deck.
        level: int
            The current amount of objects hold on deck.
        nr_resources: int
            The number of resources available (cranes).
        unloading_rate: float
            The rate at which components/units are unloaded per second.
        loading_rate: float
            The rate at which components/units are loaded per second.

    """

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)
