"""Provide an example of a site."""
# -------------------------------------------------------------------------------------!
import openclsim.core as core


# -------------------------------------------------------------------------------------!
class Site(
    core.Identifiable, core.Log, core.Locatable, core.HasContainer, core.HasResource
):
    """
    Provide a method to instantiate construction sites.
    
    The `Sites` class is a basic example on how to use OpenCLSim to
    create harbours and offshore sites. This class may also serve as a
    parent class.

    Parameters
    ----------
        env: simpy.Environment
            A SimPy simulation environment.
        registry: dict
            An empty python dictionary.
        name: str
            A name to identify the class.
        geometry: shapely.geometry.Point
            The location of the site in geojson format. Preferably by
            providing a `shapely.geometry.Point` object.
        capacity: int
            The maximum amount of objects that may be stored on site.
        level: int
            The current amount of objects hold by the site.
        nr_resources: int
            The number of resources available at site (berths, etc.).
    """

    def __init__(self, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)
