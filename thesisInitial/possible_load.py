import pandas as pd
import numpy as np


class EstimatedLoad:
    def __init__(self, av_dur, rated_power):
        self.av_dur = av_dur
        self.rated_power = rated_power

