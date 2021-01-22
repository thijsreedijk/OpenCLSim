"""Provide a basic simulation environment."""
# -------------------------------------------------------------------------------------!
import abc
import datetime

import dateutil
import simpy

import openclsim.appendix as appendix
import openclsim.model as model


# -------------------------------------------------------------------------------------!
class SimulationEnvironment(abc.ABC):
    """
    An abstract base class of the OpenCLSim simulation engine.

    The `SimulationEnvironment` class provides the user a basic example
    and guideline of how to possibly construct a simulation using
    OpenCLSim.

    Parameters
    ----------
        start_date: datetime.datetime
            A datetime object specifying the simulation start date.

    Methods
    -------
        define_offshore_environment
            class method to create an instance of the
            `OffshoreEnvironment` class.
        define_operation
            class method to define the installation operation. Within
            this function the operation should be constructed.

    Attributes
    ----------
        event_log: pandas.DataFrame
            A pandas dataframe that holds the activity log of the
            simulation. Requires the simulation to be computed.
        project_length: float
            The estimated project length in [hours]. Requires the
            simulation to be computed.
    """

    def __init__(self, start_date: datetime.datetime, *args, **kwargs):
        """Class constructor."""
        super().__init__(*args, **kwargs)

        # Define start date and time of simulation
        try:
            # Test the given start_date
            self.start_date = start_date
            start_utc = self.start_date.replace(tzinfo=dateutil.tz.UTC)
            start_epoch = start_utc.timestamp()
        except Exception:
            # Else provide the standard
            self.start_date = datetime.datetime(2020, 1, 1)
            start_utc = self.start_date.replace(tzinfo=dateutil.tz.UTC)
            start_epoch = start_utc.timestamp()

        # Initialise a SimPy simulation environment
        self.env = simpy.Environment(initial_time=start_epoch)
        self.registry = {}

        # Set default values instance attributes
        self.offshore_environment = None
        self.entities = None
        self.activities = None

    def define_offshore_environment(self):
        """Define the offshore environment (Optional)."""
        raise NotImplementedError("The offshore environment was not defined.")

    def define_entities(self):
        """Define the entities involved at operation (Optional)."""
        raise NotImplementedError("The entities were not defined.")

    @abc.abstractmethod
    def define_operation(self):
        """Define the activities of the marine operation."""
        raise NotImplementedError("At least provide some activities.")

    def initiate_simulation(self):
        """Initiate the simulation."""
        try:
            # Tests to run a complete simulation.
            self.offshore_environment = self.define_offshore_environment()
            self.entities = self.define_entities()
            self.activity = self.define_operation()

            model.register_processes([self.activity])
            self.env.run()
            return "SUCCESSFUL."

        except NotImplementedError:
            try:
                # Tests to run a minimal/simple simulation.
                self.activity = self.define_operation()

                model.register_processes([self.activity])
                self.env.run()
                return "SUCCESSFUL."
            except Exception:
                raise Exception("Aborted: suspect defining activities went wrong.")

        except Exception:
            # In any other case, simulation should be aborted.
            raise Exception("Aborted the simulation.")

    @property
    def event_log(self):
        """Return the event log."""
        # Test if user defined the simulation properly.
        assert not isinstance(
            self.activities, type(None)
        ), "`self.activities` = [..] was not defined in `define_operation`."
        assert isinstance(self.activities, list), "Expected a list of base activities."

        # Return the event log.
        return appendix.get_event_log(
            activity_list=self.activities, entities=self.entities
        )

    @property
    def project_length(self):
        """Return the project length."""
        log = self.event_log
        dt = log.Timestamp.iloc[-1] - log.Timestamp.iloc[0]
        return dt.total_seconds() / (3600)


# -------------------------------------------------------------------------------------!
