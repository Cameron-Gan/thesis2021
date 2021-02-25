import pandas as pd
import json
from os import getcwd, path

TARIFF_FILE = path.join(path.dirname(getcwd()), 'data', 'tariffs.json')


def setup_tariff_json():
    with open(TARIFF_FILE, 'w') as f:
        data = {}
        data['tariffs'] = []
        json.dump(data, f, indent=4)


def read_tariffs():
    tariffs = []
    with open(TARIFF_FILE, 'r') as tariff_json:
        data = json.load(tariff_json)
        tariffs_json = data['tariffs']
        for tariff in tariffs_json:
            tariff_type = tariff['tariff_type']
            temp = None
            if tariff_type == 'flat':
                temp = Flat()
                temp.read_tariff(tariff)
            elif tariff_type == 'TOU':
                temp = TOU()
                temp.read_tariff(tariff)
            elif tariff_type == 'TOU_controlled_load':
                temp = TOUControlledLoad()
                temp.read_tariff(tariff)
            elif tariff_type == 'flat_controlled_load':
                temp = FlatControllableLoad(tariff)
                temp.read_tariff(tariff)
            tariffs.append(temp)
    return tariffs


class Tariff:
    def __init__(self, tariff_name=None, supply_charge=None, fit=None):
        self.tariff_type = None
        self.supply_charge = supply_charge
        self.fit = fit
        self.tariff_name = tariff_name

    def get_supply_charge(self):
        return self.supply_charge

    def get_fit(self):
        return self.fit

    def get_tariff(self, time):
        return None

    def get_cost(self, grid_import_load):
        return None

    def write_tariff_type_data(self, data):
        data['tariff_type'] = self.tariff_type
        return data

    @staticmethod
    def time_in_range(time_range, check_time):
        start_time = time_range[0]
        end_time = time_range[1]
        if start_time < end_time:
            return (check_time >= start_time) & (check_time <= end_time)
        else:  # crosses midnight
            return (check_time >= start_time) | (check_time <= end_time)

    def apply_tariff(self, time, energy):
        return self.get_tariff(time) * energy

    def write_tariff(self):
        tariffs = None
        with open(TARIFF_FILE) as tf:
            temp = json.load(tf)
            tariffs = temp['tariffs']
        data = {}
        data['tariff_name'] = self.tariff_name
        data['supply_charge'] = self.supply_charge
        data['fit'] = self.fit
        data = self.write_tariff_type_data(data)
        tariffs.append(data)
        with open(TARIFF_FILE, 'w') as f:
            print('writing')
            json.dump({'tariffs': tariffs}, f, indent=4)

    def read_tariff_type_data(self, tariff_json):
        self.tariff_type = tariff_json['tariff_type']

    def read_tariff(self, tariff_json):
        self.tariff_name = tariff_json['tariff_name']
        self.supply_charge = tariff_json['supply_charge']
        self.fit = tariff_json['fit']
        self.read_tariff_type_data(tariff_json)


class Flat(Tariff):
    def __init__(self, tariff_name=None, supply_charge=None, fit=None, flat_rate=None):
        super().__init__(tariff_name=tariff_name, supply_charge=supply_charge, fit=fit)
        self.flat_rate = flat_rate
        self.tariff_type = 'flat'

    def get_tariff(self, time):
        return self.flat_rate

    def get_cost(self, grid_import_load):
        grid_import = grid_import_load.grid_import
        return grid_import * self.flat_rate

    def write_tariff_type_data(self, data):
        print(self.tariff_type)
        data['tariff_type'] = self.tariff_type
        data[self.tariff_type] = self.flat_rate
        return data

    def read_tariff_type_data(self, tariff_json):
        self.tariff_type = tariff_json['tariff_type']
        self.flat_rate = tariff_json[self.tariff_type]


class TOU(Tariff):
    def __init__(self, tariff_name=None, supply_charge=None, fit=None, tou_rate=None):
        super().__init__(tariff_name=tariff_name, supply_charge=supply_charge, fit=fit)
        self.tariff_type = 'TOU'
        self.tou_rate = tou_rate
        if tou_rate is not None: self.time_bin, self.tariff_bin = self.convert_to_binned_TOU()

    def convert_to_binned_TOU(self):
        keys = [*self.tou_rate]
        keys.sort(key=lambda tup: tup[0])
        time_bin = []
        tariff_bin = []
        for tup in keys:
            time_bin.append(tup[0])
            tariff_bin.append(self.tou_rate[tup])
        time_bin.append(24)
        return time_bin, tariff_bin

    def get_tariff(self, time):
        for period, tariff in self.tou_rate.items():
            if self.time_in_range(period, time):
                return tariff
        return None

    def get_cost(self, grid_import_load):
        grid_import = grid_import_load.grid_import
        tariff_list = self.get_tariff_from_time_index(grid_import.index.hour)
        return grid_import * tariff_list.astype(float)

    def get_tariff_from_time_index(self, times):
        tariff_from_time = pd.cut(x=times,
                                  bins=self.time_bin,
                                  labels=self.tariff_bin,
                                  include_lowest=True,
                                  ordered=False)
        return tariff_from_time

    def write_tariff_type_data(self, data):
        data['tariff_type'] = self.tariff_type
        temp_tou_rate = {}
        for period, tariff in self.tou_rate.items():
            temp_tou_rate[','.join(map(str, period))] = tariff
        data[self.tariff_type] = temp_tou_rate
        return data

    def read_tariff_type_data(self, tariff_json):
        self.tariff_type = tariff_json['tariff_type']
        tou = tariff_json[self.tariff_type]
        temp_tou_rate = {}
        for period, tariff in tou.items():
            temp_tou_rate[eval(period)] = tariff
        self.tou_rate = temp_tou_rate
        self.time_bin, self.tariff_bin = self.convert_to_binned_TOU()


class TOUControlledLoad(TOU):
    def __init__(self, tariff_name=None, supply_charge=None, fit=None, tou_rate=None, controlled_load=None):
        super().__init__(tariff_name=tariff_name, supply_charge=supply_charge, fit=fit, tou_rate=tou_rate)
        self.controlled_load_tariff = controlled_load
        self.tariff_type = 'TOU_controlled_load'

    def write_tariff_type_data(self, data):
        data['tariff_type'] = self.tariff_type
        temp_tou_rate = {}
        for period, tariff in self.tou_rate.items():
            temp_tou_rate[','.join(map(str, period))] = tariff
        data[self.tariff_type] = temp_tou_rate
        data['controlled_load_tariff'] = self.controlled_load_tariff
        return data

    def read_tariff_type_data(self, tariff_json):
        self.tariff_type = tariff_json['tariff_type']
        temp_tou_rate = {}
        for period, tariff in tariff_json[self.tariff_type].items():
            temp_tou_rate[eval(period)] = tariff
        self.tou_rate = temp_tou_rate
        self.time_bin, self.tariff_bin = self.convert_to_binned_TOU()
        self.controlled_load_tariff = tariff_json['controlled_load_tariff']

    def get_cost(self, grid_import_load):
        grid_import = grid_import_load.grid_import
        load = grid_import_load.load
        controlled_load_cost = load * self.controlled_load_tariff
        net_cost = (grid_import - load) * self.get_tariff_from_time_index(grid_import.index.hour).astype(float)
        return net_cost + controlled_load_cost


class FlatControllableLoad(Flat):
    def __init__(self, tariff_name=None, supply_charge=None, fit=None, flat_rate=None, controllable_load_tariff=None):
        super().__init__(tariff_name=tariff_name, supply_charge=supply_charge,
                         fit=fit, flat_rate=flat_rate)
        self.controllable_load_tariff = controllable_load_tariff
        self.tariff_type = 'flat_controlled_load'

    def get_cost(self, grid_import_load):
        grid_import = grid_import_load.grid_import
        load = grid_import_load.load
        load_cost = load * self.controllable_load_tariff
        net_cost = (grid_import - load) * self.flat_rate
        return net_cost + load_cost

    def write_tariff_type_data(self, data):
        data = super().write_tariff_type_data(data)
        data['controlled_load_tariff'] = self.controllable_load_tariff
        return data

    def read_tariff_type_data(self, tariff_json):
        self.tariff_type = tariff_json['tariff_type']
        self.flat_rate = tariff_json[self.tariff_type]
        self.controllable_load_tariff = tariff_json['controlled_load_tariff']