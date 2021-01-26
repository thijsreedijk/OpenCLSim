"""Add a description."""
# -------------------------------------------------------------------------------------!
import datetime
import openclsim.apps as apps
import openclsim.model as model

import shapely

# -------------------------------------------------------------------------------------!
class BaseModel(apps.SimulationEnvironment):
    """An interface of the base model."""

    def __init__(self, start_date: datetime.datetime, size: int = 1, *args, **kwargs):
        """Class constructor."""
        super().__init__(start_date, *args, **kwargs)

        # Project properties
        self.size = size

        # Define activity lengths
        self.load_component = 3600
        self.transit_to = 3600
        self.positioning = 3600
        self.install_component = 3600
        self.transit_from = 3600

    def define_offshore_environment(self):
        """Define offshore environment."""
        return None

    def define_entities(self):
        """Define entities involved during operation."""
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
        """Define installation activities."""
        # Base activities
        load_component = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="TRANSFER COMPONENT TO DECK.",
            processor=self.aeolus,
            origin=self.port,
            destination=self.aeolus,
            duration=self.load_component,
            amount=1,
        )

        transit_to_owf = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="TRANSIT TO OFFSHORE SITE.",
            mover=self.aeolus,
            destination=self.owf,
            duration=self.transit_to,
        )

        position = model.BasicActivity(
            env=self.env,
            registry=self.registry,
            name="(RE)POSITION ONTO LOCATION.",
            duration=self.positioning,
        )

        install_component = model.ShiftAmountActivity(
            env=self.env,
            registry=self.registry,
            name="INSTALL COMPONENT ON SITE.",
            processor=self.aeolus,
            origin=self.aeolus,
            destination=self.owf,
            duration=self.install_component,
            amount=1,
        )

        transit_to_port = model.MoveActivity(
            env=self.env,
            registry=self.registry,
            name="TRANSIT TO PORT.",
            mover=self.aeolus,
            destination=self.port,
            duration=self.transit_from,
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

        # List base activities and store them as a property
        self.activities = [
            load_component,
            transit_to_owf,
            position,
            install_component,
            transit_to_port,
        ]

        # Return upstream activity
        return outer_cycle
