""""WEATHER PLUGIN FOR THE VO SIMULATIONS."""
# ----------------------------------------------------------------------------!
import openclsim.model as model


# ----------------------------------------------------------------------------!
class HasDelayPlugin:
    """Mixin forActivity to initialize WeatherPluginActivity."""

    def __init__(self, delay_percentage=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if delay_percentage is not None and isinstance(
            self, model.PluginActivity
        ):

            delay_plugin = DelayPlugin(delay_percentage=delay_percentage)
            self.register_plugin(plugin=delay_plugin, priority=3)


# ----------------------------------------------------------------------------!
class DelayPlugin(model.AbstractPluginClass):
    """Mixin for all activities to add delay and downtime.

    The DelayPlugin allows the user to extend the activity length by a
    certain `delay percentage`. The user may define the delay
    percentage as either discrete valued or stochastic. If the user
    wishes to define the variable as a random variable, make sure to
    use the `scipy` package.

    Parameters
    ----------
        delay_percentage: float or scipy.stats.rv_continuous
            Either deterministic or statistically defined delay in
            percentage of the total duration. When using scipy.stats,
            make sure to define the distribution. For example,
            scipy.stats.norm(loc=0, scale=1).
    """

    def __init__(self, delay_percentage=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            if isinstance(delay_percentage, (float, int)):
                self.delay_factor = delay_percentage / 100
                self.delay_is_dist = False
            elif hasattr(delay_percentage, "rvs"):
                self.delay_factor = delay_percentage
                self.delay_is_dist = True
            elif delay_percentage is None:
                self.delay_factor = None
                self.delay_is_dist = False
            else:
                raise TypeError(
                    'delay_percentage accepts only a "float", '
                    + '"int" or "scipy.stats.rv_continuous"'
                )

        except TypeError:
            raise

    def post_process(
        self, env, activity_log, activity, start_activity, *args, **kwargs
    ):

        # Check if delay has been defined. If not no delay is added.
        if self.delay_factor is None:
            return {}

        # Check if given delay factor is a random variate.
        elif self.delay_is_dist:
            dt = env.now - start_activity
            activity_delay = dt * self.delay_factor.rvs() / 100

        # If delay is discrete valued.
        else:
            activity_delay = (env.now - start_activity) * self.delay_factor

        activity_label = {"type": "plugin", "ref": "delay"}

        return activity.delay_processing(
            env, activity_label, activity_log, activity_delay
        )
