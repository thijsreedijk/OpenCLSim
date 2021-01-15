"""Shift amount activity for the simulation."""


from functools import partial

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
        amount,
        activity_id,
    ):
        all_available = False
        while not all_available and amount > 0:
            # yield until enough content and space available in origin and destination
            yield env.all_of(
                events=[self.origin.container.get_available(amount, self.id_)]
            )

            yield from self._request_resource(
                self.requested_resources, self.processor.resource
            )
            if self.origin.container.get_level(self.id_) < amount:
                # someone removed / added content while we were requesting the processor, so abort and wait for available
                # space/content again
                self._release_resource(
                    self.requested_resources,
                    self.processor.resource,
                )
                continue

            yield from self._request_resource(
                self.requested_resources, self.origin.resource
            )
            if self.origin.container.get_level(self.id_) < amount:
                self._release_resource(
                    self.requested_resources,
                    self.processor.resource,
                )
                self._release_resource(
                    self.requested_resources,
                    self.origin.resource,
                )
                continue
            all_available = True

    def main_process_function(self, activity_log, env):
        """Origin and Destination are of type HasContainer."""
        assert self.processor.is_at(self.origin)
        assert self.destination.is_at(self.origin)

        amount = self.processor.determine_processor_amount(
            self.origin, self.destination, self.amount, self.id_
        )

        yield from self._request_resource(
            self.requested_resources, self.destination.resource
        )

        yield from self._request_resource_if_available(
            env=env,
            amount=amount,
            activity_id=activity_log.id,
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
            amount,
            activity_id=activity_log.id,
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
            self.requested_resources, self.destination.resource, self.keep_resources
        )
        if self.origin.resource in self.requested_resources:
            self._release_resource(
                self.requested_resources, self.origin.resource, self.keep_resources
            )
        if self.processor.resource in self.requested_resources:
            self._release_resource(
                self.requested_resources, self.processor.resource, self.keep_resources
            )

    def _shift_amount(
        self,
        env,
        amount,
        activity_id,
    ):
        self.processor.activity_id = activity_id
        self.origin.activity_id = activity_id

        shiftamount_fcn = self._get_shiftamount_fcn(amount)

        yield from self.processor.process(
            origin=self.origin,
            destination=self.destination,
            id_=self.id_,
            shiftamount_fcn=shiftamount_fcn,
        )

    def _get_shiftamount_fcn(self, amount):
        if self.duration is not None:
            return lambda origin, destination: (self.duration, amount)
        elif self.phase == "loading":
            return partial(self.processor.loading, amount=amount)
        elif self.phase == "unloading":
            return partial(self.processor.unloading, amount=amount)
        else:
            raise RuntimeError(
                "Both the phase (loading / unloading) and the duration of the shiftamount activity are undefined. At least one is required!"
            )
