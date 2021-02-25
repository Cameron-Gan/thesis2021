#%%

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

#%%

data = pd.read_csv('./data/data000')





first5min = data[data['reading_datetime'] == '2019-01-01 00:05:00']


site_ids = first5min['site_id'].unique()
for id in site_ids:
    site = data[data['site_id'] == id]
    with open('./data/'+str(id)+'.csv', "w") as file:
        site.to_csv(file)



