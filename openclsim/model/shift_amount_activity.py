"""Shift amount activity for the simulation."""


import numpy as np

import openclsim.core as core

from .base_activities import GenericActivity


class ShiftAmountActivity(GenericActivity):
    """
    ShiftAmountActivity Class forms a specific class for shifting material from an origin to a destination.

    It deals with a single origin container, destination container and a single processor
    to move substances from the origin to the destination. It will initiate and suspend processes
    according to a number of specified conditions. To run an activity after it has been initialized call env.run()
    on the Simpy environment with which it was initialized.


    origin: container where the source objects are located.
    destination: container, where the objects are assigned to
    processor: resource responsible to implement the transfer.
    amount: the maximum amount of objects to be transfered.
    duration: time specified in seconds on how long it takes to transfer the objects.
    id_: in case of MultiContainers the id_ of the container, where the objects should be removed from or assiged to respectively.
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    def __init__(
        self,
        processor,
        origin,
        destination,
        duration=None,
        amount=None,
        id_="default",
        show=False,
        phase=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.origin = origin
        self.destination = destination

        self.processor = processor
        self.amount = amount
        self.duration = duration
        self.id_ = id_
        self.print = show
        self.phase = phase

    def _request_resource_if_available(
        self,
        env,
        resource_requests,
        site,
        processor,
        amount,
        kept_resource,
        activity_id,
        id_="default",
        engine_order=1.0,
        verbose=False,
    ):
        all_available = False
        while not all_available and amount > 0:
            # yield until enough content and space available in origin and destination
            yield env.all_of(events=[site.container.get_available(amount, id_)])

            yield from self._request_resource(resource_requests, processor.resource)
            if site.container.get_level(id_) < amount:
                # someone removed / added content while we were requesting the processor, so abort and wait for available
                # space/content again
                self._release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                continue

            if not processor.is_at(site):
                # todo have the processor move simultaneously with the mover by starting a different process for it?
                yield from self._move_mover(
                    processor,
                    site,
                    activity_id=activity_id,
                    engine_order=engine_order,
                    verbose=verbose,
                )
                if site.container.get_level(id_) < amount:
                    # someone messed us up again, so return to waiting for space/content
                    self._release_resource(
                        resource_requests,
                        processor.resource,
                        kept_resource=kept_resource,
                    )
                    continue

            yield from self._request_resource(resource_requests, site.resource)
            if site.container.get_level(id_) < amount:
                self._release_resource(
                    resource_requests, processor.resource, kept_resource=kept_resource
                )
                self._release_resource(
                    resource_requests, site.resource, kept_resource=kept_resource
                )
                continue
            all_available = True

    def main_process_function(self, activity_log, env):
        """Origin and Destination are of type HasContainer."""
        assert self.processor.is_at(self.origin)
        assert self.destination.is_at(self.origin)

        verbose = False
        resource_requests = self.requested_resources

        if not hasattr(activity_log, "processor"):
            activity_log.processor = self.processor
        if not hasattr(activity_log, "mover"):
            activity_log.mover = self.origin
        self.amount, all_amounts = self.processor.determine_processor_amount(
            [self.origin], self.destination, self.amount, self.id_
        )

        if self.amount == 0:
            raise RuntimeError(
                f"Attempting to shift content from an empty origin ({self.origin.name}) or to a full destination ({self.destination.name}). ({all_amounts})"
            )

        yield from self._request_resource(resource_requests, self.destination.resource)

        yield from self._request_resource_if_available(
            env,
            resource_requests,
            self.origin,
            self.processor,
            self.amount,
            None,  # for now release all
            activity_log.id,
            self.id_,
            1,
            verbose=False,
        )

        if self.duration is not None:
            rate = None
        elif self.duration is not None:
            rate = self.processor.loading

        elif self.phase == "loading":
            rate = self.processor.loading
        elif self.phase == "unloading":
            rate = self.processor.unloading
        else:
            raise RuntimeError(
                "Both the pase (loading / unloading) and the duration of the shiftamount activity are undefined. At least one is required!"
            )

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )

        start_shift = env.now
        yield from self._shift_amount(
            env,
            self.processor,
            self.origin,
            self.origin.container.get_level(self.id_) + self.amount,
            self.destination,
            activity_id=activity_log.id,
            duration=self.duration,
            rate=rate,
            id_=self.id_,
            verbose=verbose,
        )

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )
        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_shift
        yield from self.post_process(**args_data)

        # release the unloader, self.destination and mover requests
        self._release_resource(
            resource_requests, self.destination.resource, self.keep_resources
        )
        if self.origin.resource in resource_requests:
            self._release_resource(
                resource_requests, self.origin.resource, self.keep_resources
            )
        if self.processor.resource in resource_requests:
            self._release_resource(
                resource_requests, self.processor.resource, self.keep_resources
            )

    def _move_mover(self, mover, origin, activity_id, engine_order=1.0, verbose=False):
        """Call the mover.move method, giving debug print statements when verbose is True."""
        # Set activity_id to mover
        mover.activity_id = activity_id
        yield from mover.move(origin, engine_order=engine_order)

    def _shift_amount(
        self,
        env,
        processor,
        origin,
        desired_level,
        destination,
        activity_id,
        duration=None,
        rate=None,
        id_="default",
        verbose=False,
    ):
        """Call the processor.process method, giving debug print statements when verbose is True."""
        amount = np.abs(origin.container.get_level(id_) - desired_level)
        # Set activity_id to processor and mover
        processor.activity_id = activity_id
        origin.activity_id = activity_id

        # Check if loading or unloading
        yield from processor.process(
            origin,
            amount,
            destination,
            id_=id_,
            duration=duration,
            rate=rate,
        )
