"""While activity for the simulation."""


import openclsim.core as core

from .base_activities import GenericActivity


class ConditionProcessMixin:
    """Mixin for the condition process."""

    def conditional_process(self, activity_log, env):
        """
        Return a generator which can be added as a process to a simpy.Environment.

        In the process the given
        self.sub_process will be executed until the given condition_event occurs. If the condition_event occurs during the execution
        of the self.sub_process, the conditional process will first complete the self.sub_process before finishing its own process.

        activity_log: the core.Log object in which log_entries about the activities progress will be added.
        env: the simpy.Environment in which the process will be run
        condition_event: a simpy.Event object, when this event occurs, the conditional process will finish executing its current
                    run of its sub_processes and then finish
        self.sub_process: an Iterable of methods which will be called with the activity_log and env parameters and should
                    return a generator which could be added as a process to a simpy.Environment
                    the sub_processes will be executed sequentially, in the order in which they are given as long
                    as the stop_event has not occurred.
        """
        condition_event = self.parse_expression(self.condition_event)

        start_time = env.now
        args_data = {
            "env": env,
            "activity_log": activity_log,
            "activity": self,
        }
        yield from self.pre_process(args_data)

        start_while = env.now

        if activity_log.log["Timestamp"]:
            if activity_log.log["Timestamp"][
                -1
            ] == "delayed activity started" and hasattr(condition_event, "__call__"):
                condition_event = condition_event()

        if hasattr(condition_event, "__call__"):
            condition_event = condition_event()
        elif type(condition_event) == list:
            condition_event = env.any_of(events=[event() for event in condition_event])

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.START,
        )
        ii = 0
        while (not condition_event.processed) and ii < self.max_iterations:
            for sub_process in self.sub_processes:
                activity_log.log_entry(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.START,
                    activity_label={
                        "type": "subprocess",
                        "ref": activity_log.id,
                    },
                )
                sub_process.start()
                yield from sub_process.call_main_proc(activity_log=sub_process, env=env)
                sub_process.end()
                activity_log.log_entry(
                    t=env.now,
                    activity_id=activity_log.id,
                    activity_state=core.LogState.STOP,
                    activity_label={
                        "type": "subprocess",
                        "ref": activity_log.id,
                    },
                )
                # work around for the event evaluation
                # this delay of 0 time units ensures that the simpy environment gets a chance to evaluate events
                # which will result in triggered but not processed events to be taken care of before further progressing
                # maybe there is a better way of doing it, but his option works for now.
                yield env.timeout(0)

            ii = ii + 1

        activity_log.log_entry(
            t=env.now,
            activity_id=activity_log.id,
            activity_state=core.LogState.STOP,
        )

        args_data["start_preprocessing"] = start_time
        args_data["start_activity"] = start_while
        yield from self.post_process(**args_data)

        yield env.timeout(0)


class WhileActivity(GenericActivity, ConditionProcessMixin):
    """
    WhileActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.

    The while activity is a structural activity, which does not require specific resources.

    sub_process: the sub_process which is executed in every iteration
    condition_event: a condition event provided in the expression language which will stop the iteration as soon as the event is fulfilled.
    start_event: the activity will start as soon as this event is triggered
                 by default will be to start immediately
    """

    #     activity_log, env, stop_event, sub_processes, requested_resources, keep_resources
    def __init__(self, sub_processes, condition_event, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""
        self.print = show
        self.sub_processes = sub_processes
        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"In While activity {self.name} the sub_process must have postpone_start=True"
                )
        self.condition_event = condition_event
        self.max_iterations = 1_000_000

        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.conditional_process, show=self.print)


class RepeatActivity(GenericActivity, ConditionProcessMixin):
    """
    RepeatActivity Class forms a specific class for executing multiple activities in a dedicated order within a simulation.

    The while activity is a structural activity, which does not require specific resources.

    Parameters
    ----------
    sub_process
        the sub_process which is executed in every iteration
    repetitions
        Number of times the subprocess is repeated
    start_event
        the activity will start as soon as this event is triggered
        by default will be to start immediately
    """

    def __init__(self, sub_processes, repetitions: int, show=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """Initialization"""

        self.print = show
        self.sub_processes = sub_processes
        for sub_process in self.sub_processes:
            if not sub_process.postpone_start:
                raise Exception(
                    f"In Repeat activity {self.name} the sub_process must have postpone_start=True"
                )
        self.max_iterations = repetitions
        self.condition_event = [
            {"type": "activity", "state": "done", "name": self.name}
        ]
        if not self.postpone_start:
            self.start()

    def start(self):
        self.register_process(main_proc=self.conditional_process, show=self.print)
