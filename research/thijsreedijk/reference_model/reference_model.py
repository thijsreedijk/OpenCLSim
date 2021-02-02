"""The reference approach to project estimation."""
# -------------------------------------------------------------------------------------!
import openclsim.apps as apps
import openclsim.plugins as plugins
import openclsim.model as model
import datetime
import shapely


# -------------------------------------------------------------------------------------!
class ReferenceModel(apps.SimulationEnvironment):
    """A reference model."""

    def __init__(self, start_date: datetime.datetime, size: int = 1, *args, **kwargs):
        """Class constructor."""
        super().__init__(start_date, *args, **kwargs)

        # Project properties
        self.size = size

        # Define activity lengths
        self.load_component = 3600
        self.transit_to = 3600 * 24 * 1
        self.positioning = 3600
        self.install_component = 3600 * 12
        self.transit_from = 3600 * 24 * 1

    def define_offshore_environment(self):
        """Define the offshore environment."""
        # Create an instance `offshore_environment`
        offshore_environment = plugins.OffshoreEnvironment()

        # Store information
        offshore_environment.store_information(
            var="Hs", filename="../data/gemini_Hs.csv", delimiter=";"
        )

        offshore_environment.store_information(
            var="Tp", filename="../data/gemini_Tp.csv", delimiter=";"
        )

        # Return the offshore environment
        return offshore_environment

    def define_entities(self):
        """Define the entities involved."""
        self.port = apps.Site(
            env=self.env,
            name="PORT",
            geometry=shapely.geometry.Point(0, 0),
            capacity=self.size,
            level=self.size,
            nr_resources=1,
        )

        self.owf = apps.Site(
            env=self.env,
            name="OWF",
            geometry=shapely.geometry.Point(1, 1),
            capacity=self.size,
            level=0,
            nr_resources=1,
        )

        self.aeolus = apps.InstallationEquipment(
            env=self.env,
            name="AEOLUS",
            geometry=self.port.geometry,
            capacity=4,
            level=0,
            nr_resources=1,
            unloading_rate=1 / 3600,
            loading_rate=1 / 3600,
            compute_v=lambda x: 10,
        )

        # Return a list of all the entities
        return [self.port, self.aeolus, self.owf]

    def define_operation(self):
        """Define the installation activities."""
        # Base activities
        load_component = apps.TransferObject(
            env=self.env,
            registry=self.registry,
            name="TRANSFER COMPONENT TO DECK.",
            duration=self.load_component,
            processor=self.aeolus,
            origin=self.port,
            destination=self.aeolus,
        )

        transit_to_owf = apps.Transit(
            env=self.env,
            registry=self.registry,
            name="TRANSIT TO OFFSHORE SITE",
            duration=self.transit_to,
            mover=self.aeolus,
            destination=self.owf,
            offshore_environment=self.offshore_environment,
            limit_expr=lambda Hs: Hs > 1,
        )

        position = model.BasicActivity(
            env=self.env,
            registry=self.registry,
            name="(RE)POSITION ONTO LOCATION.",
            duration=self.positioning,
        )

        install_component = apps.TransferObject(
            env=self.env,
            registry=self.registry,
            name="INSTALL COMPONENT TO OWF SITE.",
            duration=self.install_component,
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            offshore_environment=self.offshore_environment,
            limit_expr=lambda Hs, Tp: (Hs > 1) & (Tp > 7),
        )

        transit_to_port = apps.Transit(
            env=self.env,
            registry=self.registry,
            name="TRANSIT TO PORT.",
            duration=self.transit_from,
            mover=self.aeolus,
            destination=self.port,
            offshore_environment=self.offshore_environment,
            limit_expr=lambda Hs: Hs > 1,
        )

        # Loading cycle
        loading_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="LOAD CYCLE.",
            sub_processes=[load_component],
            condition_event={
                "or": [
                    {"type": "container", "concept": self.aeolus, "state": "full"},
                    {"type": "container", "concept": self.port, "state": "empty"},
                ]
            },
        )

        # Unload/Installation cycle
        installation_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="INSTALL CYCLE",
            sub_processes=[position, install_component],
            condition_event={
                "or": [
                    {"type": "container", "concept": self.aeolus, "state": "empty"},
                    {"type": "container", "concept": self.owf, "state": "full"},
                ]
            },
        )

        # Outer installation cycle
        outer_cycle = model.WhileActivity(
            env=self.env,
            registry=self.registry,
            name="OUTER CYCLE",
            sub_processes=[
                loading_cycle,
                transit_to_owf,
                installation_cycle,
                transit_to_port,
            ],
            condition_event={
                "or": [
                    {"type": "container", "concept": self.port, "state": "empty"},
                    {"type": "container", "concept": self.owf, "state": "full"},
                ]
            },
        )

        # Register the base activities for logging purposes.
        self.activities = [
            load_component,
            transit_to_owf,
            position,
            install_component,
            transit_to_port,
        ]

        # Return main activity for further processing.
        return outer_cycle
