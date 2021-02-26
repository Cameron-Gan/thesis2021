import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

off_threshold = 10

class ExtractLoad:
    def __init__(self, load):
        self.load = load

    def get_possible_load_date(self, date):
        load_date = self.load[date]
        possible_load = self.get_possible_load(load_date)
        possible_load.index  = load_date.index
        return possible_load

    def get_possible_load(self, l):
        days_in_set = l.index.date
        days_in_set = np.unique(days_in_set)
        possible_load = pd.DataFrame()
        for day in days_in_set:
            date = str(day)
            l_df = l.loc[date]
            l_df.loc[l_df < off_threshold] = 0
            l_np = l_df.to_numpy()
            non_zero = np.nonzero(l_np)
            start_index = non_zero[0][0]
            end_index = non_zero[0][-1]
            difference = end_index - start_index
            l_sep = l_np[start_index:end_index]
            print(l_np.size)
            for i in range(l_np.size):
                if i + difference >= l_np.size:
                    break
                y = pd.Series(np.zeros(288))
                y.iloc[i:i+difference] = l_sep
                y.rename(i, inplace=True)
                possible_load = pd.concat([possible_load, y], axis=1)

        return possible_load

