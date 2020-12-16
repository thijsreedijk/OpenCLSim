"""Component to identify the simulation objecs."""

import uuid


class Identifiable:
    """ OpenCLSim Identifiable with tags and a description.

    Parameters
    ----------
    name
        a name
    ID : UUID
        a unique id generated with uuid
    description
        Text that can be used to describe a simulation object.
        Note that this field does not influence the simulation.
    tags
        List of tags that can be used to identify objects.
        Note that this field does not influence the simulation.
    """

    def __init__(self, name: str, ID: str = None, *args, **kwargs):
        # super().__init__(*args, **kwargs)  # <= Unnecessary
        self.name = name
        self.id = ID if ID else str(uuid.uuid4())
