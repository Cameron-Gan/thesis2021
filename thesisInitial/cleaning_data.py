import pandas as pd
from os import path
from os import getcwd, listdir
import numpy as np
current_path = path.split(path.abspath(__file__))[0]
path_to_data = path.join(current_path, '..', 'data', 'houses')
# houses = listdir(path_to_data)


def is_load_in_ac_net(load, house_consumption):
    house_consumption_diff = house_consumption.diff()
    load_diff = load.diff()
    house_spikes = (house_consumption_diff.abs() > house_consumption_diff.std())
    load_spikes = (load_diff.abs() > load_diff.std())
    aligned = load_spikes & house_spikes
    # print(load_spikes)
    # print(house_spikes)

    return aligned.sum() / load_spikes.sum() > 0.05


def extract_data_from_house(house_id, load_type):
    df = pd.read_csv(path.join(path_to_data, str(house_id)+'.csv'))
    df.drop(columns=['Unnamed: 0'], inplace=True)
    df.drop_duplicates(keep='first', inplace=True)
    df['reading_datetime'] = pd.to_datetime(df['reading_datetime'])
    df.set_index('reading_datetime', inplace=True)
    df.sort_index(inplace=True)
    df['circuit_id_monitor'] = df.circuit_id.astype(str) + ' <<' + df.monitors + '>>'

    original_set = df.reset_index()
    original_set = original_set.pivot(index='reading_datetime', columns='circuit_id_monitor',
                                      values=['energy', 'energy_pos', 'energy_neg'])
    net_energy = original_set[:]['energy']

    load = net_energy.filter(regex=load_type).sum(axis=1).rename('load')
    PV = net_energy.filter(regex='pv_site_net').sum(axis=1).rename('PV')
    AC = net_energy.filter(regex='ac_load_net').sum(axis=1).rename('AC')
    total_use = AC + PV

    if is_load_in_ac_net(load, total_use):
        total_use = total_use
        grid_import = AC.clip(lower=0)
        grid_export = (AC * - 1).clip(lower=0)
    else:
        total_use = total_use + load
        grid_import = (AC + load).clip(lower=0)
        grid_export = ((AC + load) * - 1).clip(lower=0)
    total_use = total_use.rename('total_use')
    grid_import = grid_import.rename('grid_import')
    grid_export = grid_export.rename('grid_export')

    data = pd.concat([load, PV, AC, total_use, grid_import, grid_export], axis=1)
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
