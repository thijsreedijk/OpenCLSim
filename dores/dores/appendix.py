''' FILE CONTAINING A NUMBER OF USEFUL PYTHON FUNCTIONS '''
# ----------------------------------------------------------------------------!
import scipy.stats as st
import numpy as np


# ----------------------------------------------------------------------------!
def lognorm(mean, std):
    mu = np.log(mean ** 2 / np.sqrt(mean ** 2 + std ** 2))
    sigma = np.sqrt(np.log(1 + std ** 2 / mean ** 2))
    return st.lognorm(s=sigma, scale=np.exp(mu))
