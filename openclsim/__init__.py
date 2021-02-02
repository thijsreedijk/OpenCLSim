"""Top-level package for OpenCLSim."""

# import pkg_resources

import openclsim.appendix as appendix
import openclsim.apps as apps
import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugins

__author__ = """Mark van Koningsveld"""
__email__ = "M.vanKoningsveld@tudelft.nl"
__version__ = "1.2.3"
__all__ = ["model", "plugins", "core", "plot", "appendix", "apps"]
# __version__ = pkg_resources.get_distribution(__name__).version
