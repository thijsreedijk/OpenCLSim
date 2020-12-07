"""Test package."""
import shapely.geometry
import simpy

import openclsim.core as core
import openclsim.model as model

from .test_utils import assert_log


def test_wraped_single_run():
    """Test wraped single run."""
    # setup environment
    simulation_start = 0
    my_env = simpy.Environment(initial_time=simulation_start)

    Site = type(
        "Site",
        (
            core.Identifiable,
            core.Log,
            core.Locatable,
            core.HasContainer,
            core.HasResource,
        ),
        {},
    )

    TransportProcessingResource = type(
        "TransportProcessingResource",
        (
            core.Identifiable,
            core.Log,
            core.ContainerDependentMovable,
            core.Processor,
            core.LoadingFunction,
            core.UnloadingFunction,
            core.HasResource,
        ),
        {},
    )

    location_from_site = shapely.geometry.Point(4.18055556, 52.18664444)  # lon, lat
    location_to_site = shapely.geometry.Point(4.25222222, 52.11428333)  # lon, lat

    data_from_site = {
        "env": my_env,
        "name": "Winlocatie",
        "geometry": location_from_site,
        "capacity": 5_000,
        "level": 5_000,
    }

    data_to_site = {
        "env": my_env,
        "name": "Dumplocatie",
        "geometry": location_to_site,
        "capacity": 5_000,
        "level": 0,
    }

    from_site = Site(**data_from_site)
    to_site = Site(**data_to_site)

    data_hopper = {
        "env": my_env,
        "name": "Hopper 01",
        "geometry": location_from_site,
        "capacity": 1000,
        "compute_v": lambda x: 10 + 2 * x,
        "loading_rate": 1,
        "unloading_rate": 5,
    }

    hopper = TransportProcessingResource(**data_hopper)

    model.single_run_process(
        name="single_run",
        registry={},
        env=my_env,
        origin=from_site,
        destination=to_site,
        mover=hopper,
        loader=hopper,
        unloader=hopper,
    )

    my_env.run()

    assert my_env.now == 13699.734162066252

    assert_log(hopper.log)
    assert_log(from_site.log)
    assert_log(to_site.log)
