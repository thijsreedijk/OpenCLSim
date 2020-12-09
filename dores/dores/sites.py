'''' CONTAINS CLASSES FOR GENERATING SITES SUCH AS PORTS AND OWFs. '''
# ----------------------------------------------------------------------------!
import simpy


# ----------------------------------------------------------------------------!
class Site(object):
    '''
    -------------------------------------------------------------------
    Description:
        Python object used for describing the sites involved in
        constructing the offshore wind farm, such as a port and the
        offshore area. Holds information on the number of components in
        stock and installed, but also their specific location.
    -------------------------------------------------------------------
    Parameters:
        ID: str
            Name or identification of the site.
        env: simpy.Environment
            A simpy environment in which the simulation is carried out.
    -------------------------------------------------------------------
    '''

    instances = []

    def __init__(self, ID: str, env: simpy.Environment, capacity: int,
                 level: int, resources: int, **kwargs):

        # Assign arguments to class attributes
        self.__dict__ = locals()

        # Initialise stock using the SimPy container
        self.container = simpy.Container(env=self.env, capacity=capacity,
                                         init=level)

        # Initialise number of available berths using the SimPy resource
        self.resource = simpy.Resource(env=self.env, capacity=resources)

        # Add instance to list of instances
        Site.instances.append(self)
