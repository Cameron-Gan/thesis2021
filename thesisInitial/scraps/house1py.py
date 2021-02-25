#%%

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

#%%

data = pd.read_csv('./data/house1.csv')
data.drop('Unnamed: 0', axis=1, inplace=True)
data['reading_datetime'] = pd.to_datetime(data.reading_datetime)
data.sort_values('reading_datetime')

#%%
    
# net = df[df.monitors == 'ac_load_net']
net = data
net = net.set_index('reading_datetime')
net.info()
# net.info()

#%%

# slice = net['2019-01-01']
from datetime import datetime
# for date in pd.date_range(pd.datetime(2019,1,1), pd.datetime(2019,2,1), freq='D'):
#     # print(date.strftime('%D'))
# #     sns.lineplot(x='reading_datetime', y='energy', data=net[date].reset_index())
# # plt.show()
#
# t = pd.DataFrame(net[net.monitors == 'ac_load_net'].energy)
# t = t.resample('1h').sum()
#
#
# other = t.set_index((t.index.hour), append=True)['energy'].unstack().plot.bar()
#
# plt.show()
# # unstacked.barplot()
# #%%
# other['energy'].unstack().plot.bar()
# plt.show()


#%%

# df = net['2019-01':'2019-02'].reset_index()
# df = pd.concat([df, net['2019-12'].reset_index()])
# df = df.set_index('reading_datetime')
# df = df.sort_index()
df = net[net.monitors == 'ac_load_net'].drop_duplicates()
df = df['energy'].resample('30min').sum()
df = pd.DataFrame(df)
# dups = df.drop_duplicates()
# print(dups.loc[pd.Timestamp('2019-01-01T00:55:00')])

#
# total = net[net.monitors == 'ac_load_net']
# ac = net[net.monitors == 'load_air_conditioner']
#
# both = pd.DataFrame(ac.energy)
# both['total'] = total.energy
#

# other = df.set_index(roundTime(df.index.minute, 5*60), append=True)
#
other = df.set_index((df.index.hour + df.index.minute/60), append=True).drop_duplicates()
ax = other['energy'].unstack().plot.box(figsize=(15, 10))
ax.set_ylabel('Net Energy Consumption (W)')
ax.set_xlabel('Day Hour')
ax.set_title('House 2 Batter Load Profile over 2019')
plt.xticks(rotation=45)
# plt.xticks(np.arange(0,(24*60)/5,12), np.arange(0,24))
plt.show()
#
# # dup = net.drop_duplicates()
# # plt.show()
# # new.plot(label='summer')
# # df = net['2019-03':'2019-05'].reset_index()
# # new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
# # new.plot(label='autumn')
# # df = net['2019-06':'2019-08'].reset_index()
# # new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
# # new.plot(label='winter')
# # df = net['2019-09':'2019-11'].reset_index()
# # new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
# new.plot(label='spring')
# plt.show()

