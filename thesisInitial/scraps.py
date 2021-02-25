#%%
#
# houses_w_battery =
# # data.tail()

#%%

# house1_id = data.site_id.unique()[0]
house1 = data[data.site_id == 91341]


house1.info()
df = house1.sort_values('reading_datetime')
df.to_csv('./data/house3.csv')

#%%

# net = df[df.monitors == 'ac_load_net']
net = df.copy()
net = net.set_index('reading_datetime')
# net.info()

#%%

# slice = net['2019-01-01']
from datetime import datetime
for date in pd.date_range(pd.datetime(2019,1,1), pd.datetime(2019,2,1), freq='D'):
    # print(date.strftime('%D'))
    sns.lineplot(x='reading_datetime', y='energy', data=net[date.strftime('%D')].reset_index())
plt.show()

#%%

df = net['2019-01':'2019-02'].reset_index()
df = pd.concat([df, net['2019-12'].reset_index()])
new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
new.plot(label='summer')
df = net['2019-03':'2019-05'].reset_index()
new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
new.plot(label='autumn')
df = net['2019-06':'2019-08'].reset_index()
new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
new.plot(label='winter')
df = net['2019-09':'2019-11'].reset_index()
new = df.groupby([df.reading_datetime.dt.time])['energy'].mean()
new.plot(label='spring')
plt.legend()

#%%
