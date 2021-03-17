import pandas as pd
from os import path
from os import getcwd, listdir
import numpy as np
current_path = path.split(path.abspath(__file__))[0]
path_to_data = path.join(current_path, '..', 'data', 'houses')
# houses = listdir(path_to_data)


def prepare_features(data):
    location = data['Location'][0]

    data['total_use_wo_load'] = data['total_use'] - data['load']

    temperature_df = pd.read_csv(path.join(path_to_data, '..', 'weather', location+'_Airport_Temp.csv'), index_col=0, parse_dates=True)
    temperature_df = temperature_df.loc['2019']
    insolation_df = pd.read_csv(path.join(path_to_data, '..', 'weather', location+'_Airport_Insolation.csv'), index_col=0, parse_dates=True)
    insolation_df = insolation_df.loc['2019']

    sample_rated = data['total_use_wo_load'].resample('5T').sum()
    max_load = sample_rated.resample('24h').max().shift(1).rename('daily_max')

    temperature_df = temperature_df.drop(columns='Minimum temperature (Degree C)')

    feature_set = data.resample('24h').sum() / 1000
    feature_set = pd.concat([feature_set, temperature_df, insolation_df, max_load], axis=1)
    feature_set['month'] = feature_set.index.month
    feature_set = pd.concat([feature_set, feature_set['total_use_wo_load'].shift(1).rename('previous_day')], axis=1)
    feature_set = pd.concat([feature_set, feature_set['total_use_wo_load'].shift(2).rename('second_previous_day')], axis=1)
    feature_set = pd.concat([feature_set, feature_set['total_use_wo_load'].shift(7).rename('previous_week')], axis=1)
    feature_set['weekend_weekday'] = (feature_set.index.dayofweek < 5) * 1
    feature_set['dayofweek'] = feature_set.index.dayofweek
    feature_set['dates'] = feature_set.index
    # for col in ['load', 'PV', 'AC', 'total_use', 'total_use_wo_load']: feature_set[col] = feature_set[col] / 1000
    return feature_set


def is_load_in_ac_net(load, house_consumption):
    house_consumption_diff = house_consumption.diff()
    load_diff = load.diff()
    house_spikes = (house_consumption_diff.abs() > house_consumption_diff.std())
    load_spikes = (load_diff.abs() > load_diff.std())
    aligned = load_spikes & house_spikes
    # print(load_spikes)
    # print(house_spikes)

    return aligned.sum() / load_spikes.sum() > 0.05


def extract_data_from_house(house_id, load_on=False):
    df = pd.read_feather(path.join(path_to_data, str(house_id)+'_feather'))

    location = df['Location'][0]
    load_type = df['load_type'][0]
    df.drop(columns=['Location', 'load_type'], inplace=True)

    df.drop_duplicates(keep='first', inplace=True)
    df['reading_datetime'] = pd.to_datetime(df['reading_datetime'])
    df.set_index('reading_datetime', inplace=True)
    df.sort_index(inplace=True)
    df['circuit_id_monitor'] = df.circuit_id.astype(str) + ' <<' + df.monitors + '>>'

    original_set = df.reset_index()
    original_set = original_set.pivot(index='reading_datetime', columns='circuit_id_monitor',
                                      values=['energy', 'energy_pos', 'energy_neg'])
    net_energy = original_set[:]['energy']

    PV = net_energy.filter(regex='pv_site_net').sum(axis=1).rename('PV')
    AC = net_energy.filter(regex='ac_load_net').sum(axis=1).rename('AC')
    total_use = AC + PV
    load = pd.Series(index=total_use.index, data=np.zeros(len(net_energy.index)), name='load')
    location = pd.Series(index=total_use.index,
                         data=[location for i in range(len(net_energy.index))],
                         name='Location')

    if load_on and type(load_type) == str:
        load = net_energy.filter(regex=load_type).sum(axis=1).rename('load')
        if not(is_load_in_ac_net(load, total_use)):
            total_use = total_use + load

    grid_import  = (total_use - PV).clip(lower=0)
    grid_export  = ((total_use - PV) * -1).clip(lower=0)
    total_use = total_use.rename('total_use')
    grid_import = grid_import.rename('grid_import')
    grid_export = grid_export.rename('grid_export')

    data = pd.concat([location, load, PV, AC, total_use, grid_import, grid_export], axis=1)
    idx = pd.date_range(start='2019-01-01 00:00:00', end='2019-12-31 23:55:00', freq='5T')
    data = data.reindex(idx, fill_value=0)
    return data


def apply_new_load(data, new_load):
    new_load = new_load.rename('load')
    new_total_use = data.total_use - data.load + new_load
    new_AC = new_total_use - data.PV
    new_grid_import = new_AC.clip(lower=0)
    new_grid_export = (new_AC * -1).clip(lower=0)
    new_data = pd.concat([new_load, data.PV, new_AC, new_total_use, new_grid_import, new_grid_export], axis=1)
    return new_data


def extract_rated_power(load):
    load_analysis = pd.DataFrame()
    load_analysis['power'] = (load * 12) / 1000
    rated_power = load_analysis.power.max()
    load_analysis['on_time'] = (load_analysis.power / rated_power)
    period = 0.9
    on = load_analysis.loc[load_analysis.on_time > period].power
    rated_power = on.median()
    return rated_power


def extract_average_time_on(load):
    load_analysis = pd.DataFrame()
    load_analysis['power'] = (load * 12) / 1000
    rated_power = load_analysis.power.max()
    load_analysis['on_time'] = (load_analysis.power / rated_power)
    period = 0.9
    on = load_analysis.loc[load_analysis.on_time > period].power
    load_analysis['on_time'] = load_analysis['on_time'] * 5
    load_24h = load_analysis.resample('24h', offset=12).sum()
    non_zero_days = load_24h[load_24h.on_time > 20].on_time
    average_duration = non_zero_days.mean()
    return average_duration

# seasons = [
#             ('summer', [12, 1, 2]),
#             ('autumn', [3, 4, 5]),
#             ('winter', [6, 7, 8]),
#             ('spring', [9, 10, 11])
#           ]

def extract_season_median_load_profile(data):
    median_data = data.copy(deep=True)
    median_data['total_use_WO_load'] = median_data['total_use'] - median_data['load']
    median_data.loc[:, 'Dates'] = median_data.index
    median_data.loc[:, "Time"] = median_data.index.time
    summer = median_data['2019-12'].append(median_data['2019-01':'2019-02'])
    autumn = median_data['2019-03':'2019-05']
    winter = median_data['2019-06':'2019-08']
    spring = median_data['2019-09':'2019-11']
    spring_pivot = spring.pivot(index='Time', columns='Dates', values='total_use_WO_load')
    spring_pivot.loc[:, 'median'] = spring_pivot.median(axis=1)
    spring_pivot.loc[:, 'mean'] = spring_pivot.mean(axis=1)
    winter_pivot = winter.pivot(index='Time', columns='Dates', values='total_use_WO_load')
    winter_pivot.loc[:, 'median'] = winter_pivot.median(axis=1)
    winter_pivot.loc[:, 'mean'] = winter_pivot.mean(axis=1)
    summer_pivot = summer.pivot(index='Time', columns='Dates', values='total_use_WO_load')
    summer_pivot.loc[:, 'median'] = summer_pivot.median(axis=1)
    summer_pivot.loc[:, 'mean'] = summer_pivot.mean(axis=1)
    autumn_pivot = autumn.pivot(index='Time', columns='Dates', values='total_use_WO_load')
    autumn_pivot.loc[:, 'median'] = autumn_pivot.median(axis=1)
    autumn_pivot.loc[:, 'mean'] = autumn_pivot.mean(axis=1)

    normalised_median = pd.DataFrame()
    normalised_median['spring'] = spring_pivot['median'] / spring_pivot['median'].sum()
    normalised_median['summer'] = summer_pivot['median'] / summer_pivot['median'].sum()
    normalised_median['winter'] = winter_pivot['median'] / winter_pivot['median'].sum()
    normalised_median['autumn'] = autumn_pivot['median'] / autumn_pivot['median'].sum()
    return normalised_median


# generates a load based on average runtime and rated power
def generate_load(index, start_time, av_dur, rated_pow):
    duration = pd.Timedelta(value=av_dur, unit='m')
    start_time = pd.Timestamp(index[0]) + pd.Timedelta(value=start_time * 5, unit='m')
    end_time = start_time + duration
    break_flag = False
    if end_time.date() > start_time.date():
        break_flag = True
    # print(end_time)
    y = pd.Series(np.zeros(len(index)), index = index)
    y[start_time:end_time] = (rated_pow / 12) * 1000
    return y, break_flag


# TODO extract the actual load from the day
def extract_load(load):
    load.loc[load < 0.5] = 0



def find_min(data, tariff):
    min_cost_load = pd.Series(dtype='float64')
    days_in_set = data['2019-01'].index.date
    days_in_set = np.unique(days_in_set)
    for day in days_in_set:
        date = str(day)
        total_use_without_load = data[date].total_use - data[date].load
        pv_day = data.PV[date]
        grid_import_cost = tariff.get_cost(data[date][['grid_import', 'load']] / 1000).sum()
        grid_export_revenue = data[date]['grid_export'] / 1000 * tariff.get_fit()
        min_cost = grid_import_cost.sum() - grid_export_revenue.sum()
        # print('minCostBefore' + str(min_cost))
        start = time.time()
        max_time = 0
        max_load = data[date].load
        index = total_use_without_load.index
        for i in range(int((24 * 60) / 5)):
            new_load, break_flag = generate_load(index, i)
            if break_flag: break
            new_load = new_load.rename('load')
            new_total_use = total_use_without_load + new_load
            new_grid_import = (new_total_use - pv_day).clip(lower=0).rename('grid_import')
            new_grid_export = ((new_total_use - pv_day) * -1).clip(lower=0)
            new_grid_import_cost = tariff.get_cost(pd.concat([new_grid_import / 1000, new_load / 1000], axis=1))
            new_grid_export_revenue = (new_grid_export / 1000) * tariff.get_fit()
            new_cost_net = new_grid_import_cost.sum(axis=0) - new_grid_export_revenue.sum(axis=0)
            if new_cost_net < min_cost:
                min_cost = new_cost_net
                max_load = new_load
                max_time = i

        min_cost_load = pd.concat([min_cost_load, max_load], axis=0)
        # print(time.time() - start)
        # print('MinCostAfter' + str(min_cost))

    min_cost_load = min_cost_load.rename('new_load')

def find_min_cost():
    for day in days_in_set:
        date = str(day)
        total_use_without_load = data[date].total_use - data[date].load
        pv_day = data.PV[date]
        grid_import_cost = tariff.get_cost(data[date][['grid_import', 'load']] / 1000).sum()
        grid_export_revenue = data[date]['grid_export'] / 1000 * tariff.get_fit()
        min_cost = grid_import_cost.sum() - grid_export_revenue.sum()
        # print('minCostBefore' + str(min_cost))
        max_time = 0
        max_load = data[date].load
        index = total_use_without_load.index
        tariff_series = tariff.get_tariff_from_time_index(index.hour).astype(float)
        for i in range(int((24 * 60) / 5)):
            new_load, break_flag = generate_load(index, i)
            if break_flag:
                break
            new_load = new_load
            new_total_use = total_use_without_load + new_load
            new_grid_import = (new_total_use - pv_day).clip(lower=0)
            new_grid_export = ((new_total_use - pv_day) * -1).clip(lower=0)
            new_grid_import_cost = (new_grid_import / 1000) * tariff_series
            new_grid_export_revenue = (new_grid_export / 1000) * tariff.get_fit()
            new_cost_net = new_grid_import_cost.sum(axis=0) - new_grid_export_revenue.sum(axis=0)
            if new_cost_net < min_cost:
                min_cost = new_cost_net
                max_load = new_load
                max_time = i

        min_cost_load = pd.concat([min_cost_load, max_load], axis=0)
    print(time.time() - start)

    # def get_cost_for_day(new_load, total_use_without_load, pv_day):
    #     new_total_use = total_use_without_load + new_load
    #     new_grid_import = (new_total_use - pv_day).clip(lower=0)
    #     new_grid_export = ((new_total_use - pv_day) * -1).clip(lower=0)
    #     new_grid_import_cost = (new_grid_import / 1000) * tariff_series
    #     new_grid_export_revenue = (new_grid_export / 1000) * tariff.get_fit()
    #     # new_cost_net = new_grid_import_cost.sum(axis=0) - new_grid_export_revenue.sum(axis=0)
    #     return pd.Series([new_grid_import_cost, new_grid_export_revenue], index=['cost', 'revenue'])
    # load_options = pd.DataFrame()
    # for i in range(int((24 * 60) / 5)):
    #     new_load = generate_load(data['2019-01-01'], i)
    #     load_options = pd.concat([load_options, new_load], axis=1)
