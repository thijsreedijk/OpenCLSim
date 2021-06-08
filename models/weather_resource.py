import numpy as np


def vector_magnitude(x):
    return np.sqrt(np.sum(x.dot(x)))
