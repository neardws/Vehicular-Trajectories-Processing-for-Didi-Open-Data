import pandas as pd
import numpy as np
import time
from typing import Optional

class vehicleTrajectoriesProcessor(object):
    def __init__(
        self, 
        file_name: str, 
        longitude_min: float, 
        latitude_min: float,
        map_width: float,
        time_start: str, 
        time_end: str, 
        out_file: str,
        output_analysis: Optional[bool] = False,
    ) -> None:
        """The constructor of the class."""
        """
        Args:
            file_name: the name of the file to be processed. 
                e.g., '/CSV/gps_20161116', source: Didi chuxing gaia open dataset initiative
            longitude_min: the minimum longitude of the bounding box. e.g., 104.04565967220308
            latitude_min: the minimum latitude of the bounding box. e.g., 30.654605745741608
            map_width: the width of the bounding box. e.g., 500 (meters)
            time_start: the start time. e.g., '2016-11-16 08:00:00'
            time_end: the end time. e.g., '2016-11-16 08:05:00'
            out_file: the name of the output file.  e.g., '/CSV/gps_20161116_processed.csv'
        """
        self._file_name = file_name
        self._longitude_min, self._latitude_min = self.gcj02_to_wgs84(longitude_min, latitude_min)
        self._map_width = map_width
        self._time_start = time_start
        self._time_end = time_end
        self._out_file = out_file
        self._output_analysis : bool = output_analysis
        
        self._longitude_max, self._latitude_max = self.get_longitude_and_latitude_max(
            self._longitude_min, self._latitude_min, self._map_width)
        
        self.process(
            map_width=self._map_width,
            longitude_min=self._longitude_min, 
            latitude_min=self._latitude_min, 
            out_file=self._out_file
        )

    def get_longitude_and_latitude_max(self, longitude_min, latitude_min, map_width) -> tuple:
        longitude_max = longitude_min
        latitude_max = latitude_min
        precision = 5 * 1e-1   
        """
        += 1e-2 add 1467 meters
        += 1e-3 add 147 meters
        += 1e-4 add 15 meters
        += 1e-5 add 1 meter
        += 1e-6 add 0.25 meters
        """
        length = np.sqrt(2) * map_width
        while(True):
            distance = self.get_distance(longitude_min, latitude_min, longitude_max, latitude_max)
            if np.fabs(distance - length) < precision:
                break
            if np.fabs(distance - length) > 2000.0:
                longitude_max += 1e-2
                latitude_max += 1e-2
            if np.fabs(distance - length) > 150.0 and np.fabs(distance - length) <= 2000.0:
                longitude_max += 1e-3
                latitude_max += 1e-3
            if np.fabs(distance - length) > 15.0 and np.fabs(distance - length) <= 150.0:
                longitude_max += 1e-4
                latitude_max += 1e-4
            if np.fabs(distance - length) > 1.0 and np.fabs(distance - length) <= 15.0:
                longitude_max += 1e-5
                latitude_max += 1e-5
            if np.fabs(distance - length) <= 1.0:
                longitude_max += 1e-6
                latitude_max += 1e-6
        return longitude_max, latitude_max

    def process(
        self, 
        map_width, 
        longitude_min, 
        latitude_min, 
        out_file, 
    ) -> None:

        time_style = "%Y-%m-%d %H:%M:%S"
        time_start_array = time.strptime(self._time_start, time_style)
        time_end_array = time.strptime(self._time_end, time_style)
        time_start = int(time.mktime(time_start_array))
        time_end = int(time.mktime(time_end_array))

        df = pd.read_csv(
            self._file_name, 
            names=['vehicle_id', 'order_number', 'time', 'longitude', 'latitude'], 
            header=0
        )
        # 经纬度定位
        df.drop(df.columns[[1]], axis=1, inplace=True)
        df.dropna(axis=0)

        longitude_max, latitude_max = self.get_longitude_and_latitude_max(longitude_min, latitude_min, map_width)
        
        df = df[
            (df['longitude'] > longitude_min) & 
            (df['longitude'] < longitude_max) & 
            (df['latitude'] > latitude_min) & 
            (df['latitude'] < latitude_max) & 
            (df['time'] > time_start) & 
            (df['time'] < time_end)]  # location
        
        # sorted
        df.sort_values(by=['vehicle_id', 'time'], inplace=True, ignore_index=True)

        vehicle_number = 0
        old_vehicle_id = None
        for index, row in df.iterrows():

            row = dict(df.iloc[index])
            vehicle_id = row['vehicle_id']

            if old_vehicle_id:
                if vehicle_id == old_vehicle_id:
                    row['vehicle_id'] = vehicle_number
                    longitude, latitude = self.gcj02_to_wgs84(float(row['longitude']), float(row['latitude']))
                    row['time'] = row['time'] - time_start
                    x = self.get_distance(longitude_min, latitude_min, longitude, latitude_min)
                    y = self.get_distance(longitude_min, latitude_min, longitude_min, latitude)
                    row['longitude'] = x
                    row['latitude'] = y
                    df.iloc[index] = pd.Series(row)
                else:
                    vehicle_number += 1
                    row['vehicle_id'] = vehicle_number
                    longitude, latitude = self.gcj02_to_wgs84(float(row['longitude']), float(row['latitude']))
                    row['time'] = row['time'] - time_start
                    x = self.get_distance(longitude_min, latitude_min, longitude, latitude_min)
                    y = self.get_distance(longitude_min, latitude_min, longitude_min, latitude)
                    row['longitude'] = x
                    row['latitude'] = y
                    df.iloc[index] = pd.Series(row)
            else:
                row['vehicle_id'] = vehicle_number
                longitude, latitude = self.gcj02_to_wgs84(float(row['longitude']), float(row['latitude']))
                row['time'] = row['time'] - time_start
                x = self.get_distance(longitude_min, latitude_min, longitude, latitude_min)
                y = self.get_distance(longitude_min, latitude_min, longitude_min, latitude)
                row['longitude'] = x
                row['latitude'] = y
                df.iloc[index] = pd.Series(row)

            old_vehicle_id = vehicle_id
            
        if self._output_analysis:
            df.to_csv(out_file + "_without_fill" + ".csv")
        
        old_row = None
        for index, row in df.iterrows():
            new_row = dict(df.iloc[index])
            if old_row:
                if old_row['vehicle_id'] == new_row['vehicle_id']:
                    add_number = int(new_row['time']) - int(old_row['time']) - 1
                    if add_number > 0:
                        add_longitude = (float(new_row['longitude']) - float(old_row['longitude'])) / float(add_number)
                        add_latitude = (float(new_row['latitude']) - float(old_row['latitude'])) / float(add_number)
                        for time_index in range(add_number):
                            df = pd.concat([df, pd.DataFrame({
                                    'vehicle_id': [old_row['vehicle_id']],
                                    'time': [old_row['time'] + time_index + 1],
                                    'longitude': [old_row['longitude'] + (time_index + 1) * add_longitude],
                                    'latitude': [old_row['latitude'] + (time_index + 1) * add_latitude]})],
                                axis=0,
                                ignore_index=True)
                else:
                    if old_row['time'] < time_end - time_start:
                        for time_index in range(time_end - time_start - int(old_row['time']) - 1):
                            df = pd.concat([df, pd.DataFrame({
                                    'vehicle_id': [old_row['vehicle_id']],
                                    'time': [old_row['time'] + time_index + 1],
                                    'longitude': [old_row['longitude']],
                                    'latitude': [old_row['latitude']]})],
                                axis=0,
                                ignore_index=True)
                    if new_row['time'] > 0:
                        for time_index in range(int(new_row['time'])):
                            df = pd.concat([df, pd.DataFrame({
                                    'vehicle_id': [new_row['vehicle_id']],
                                    'time': [time_index],
                                    'longitude': [new_row['longitude']],
                                    'latitude': [new_row['latitude']]})],
                                axis=0,
                                ignore_index=True)
                old_row = new_row
            else:
                if new_row['time'] > 0:
                    for time_index in range(int(new_row['time'])):
                        df = pd.concat([df, pd.DataFrame({
                                'vehicle_id': [new_row['vehicle_id']],
                                'time': [time_index],
                                'longitude': [new_row['longitude']],
                                'latitude': [new_row['latitude']]})],
                            axis=0,
                            ignore_index=True)
                old_row = new_row
        df.sort_values(by=['vehicle_id', 'time'], inplace=True, ignore_index=True)
        df.to_csv(out_file + ".csv")
        
        if self._output_analysis:
            analyst = vehicleTrajectoriesAnalyst(
                trajectories_file_name=out_file + ".csv",
                trajectories_file_name_with_no_fill=out_file + "_without_fill" + ".csv",
                during_time=time_end - time_start,
            )
            analyst.output_characteristics()

    def get_out_file(self):
        return self._out_file

    def gcj02_to_wgs84(self, lng: float, lat: float):
        """
        GCJ02(火星坐标系)转GPS84
        :param lng:火星坐标系的经度
        :param lat:火星坐标系纬度
        :return:
        """
        a = 6378245.0  # 长半轴
        ee = 0.00669342162296594323

        d_lat = self.trans_form_of_lat(lng - 105.0, lat - 35.0)
        d_lng = self.trans_form_of_lon(lng - 105.0, lat - 35.0)

        rad_lat = lat / 180.0 * np.pi
        magic = np.sin(rad_lat)
        magic = 1 - ee * magic * magic
        sqrt_magic = np.sqrt(magic)

        d_lat = (d_lat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * np.pi)
        d_lng = (d_lng * 180.0) / (a / sqrt_magic * np.cos(rad_lat) * np.pi)
        mg_lat = lat + d_lat
        mg_lng = lng + d_lng
        return [lng * 2 - mg_lng, lat * 2 - mg_lat]

    def trans_form_of_lat(self, lng: float, lat: float):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
            0.1 * lng * lat + 0.2 * np.sqrt(np.fabs(lng))
        ret += (20.0 * np.sin(6.0 * lng * np.pi) + 20.0 *
                np.sin(2.0 * lng * np.pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(lat * np.pi) + 40.0 *
                np.sin(lat / 3.0 * np.pi)) * 2.0 / 3.0
        ret += (160.0 * np.sin(lat / 12.0 * np.pi) + 320 *
                np.sin(lat * np.pi / 30.0)) * 2.0 / 3.0
        return ret

    def trans_form_of_lon(self, lng: float, lat: float):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
            0.1 * lng * lat + 0.1 * np.sqrt(np.fabs(lng))
        ret += (20.0 * np.sin(6.0 * lng * np.pi) + 20.0 *
                np.sin(2.0 * lng * np.pi)) * 2.0 / 3.0
        ret += (20.0 * np.sin(lng * np.pi) + 40.0 *
                np.sin(lng / 3.0 * np.pi)) * 2.0 / 3.0
        ret += (150.0 * np.sin(lng / 12.0 * np.pi) + 300.0 *
                np.sin(lng / 30.0 * np.pi)) * 2.0 / 3.0
        return ret

    def get_distance(self, lng1: float, lat1: float, lng2: float, lat2: float) -> float:
        """ return the distance between two points in meters """
        lng1, lat1, lng2, lat2 = map(np.radians, [float(lng1), float(lat1), float(lng2), float(lat2)])
        d_lon = lng2 - lng1
        d_lat = lat2 - lat1
        a = np.sin(d_lat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(d_lon / 2) ** 2
        distance = 2 * np.arcsin(np.sqrt(a)) * 6371 * 1000
        distance = round(distance / 1000, 3)
        return distance * 1000

    def get_longitude_min(self) -> float:
        return self._longitude_min
    
    def get_longitude_max(self) -> float:
        return self._longitude_max

    def get_latitude_min(self) -> float:
        return self._latitude_min

    def get_latitude_max(self) -> float:
        return self._latitude_max
    
    
class vehicleTrajectoriesAnalyst(object):
    def __init__(
        self, 
        trajectories_file_name: str,
        trajectories_file_name_with_no_fill: str,
        during_time: int,
    ) -> None:
        """Output the analysis of vehicular trajcetories, including
            average dwell time (s) of vehicles: ADT
            standard deviation of dwell time (s) of vehicles: ADT_STD
            average number of vehicles in each second: ANV
            standard deviation of number of vehicles in each second: ANV_STD
            average speed (m/s) of vehicles: ASV
            standard deviation of speed (m/s) of vehicles: ASV_STD

        Args:
            trajectories_file_name (str): file with processed trajectories
            trajectories_file_name_with_no_fill (str): file with processed trajectories without filling
            during_time (int): e.g., 300 s
        """
        self._trajectories_file_name = trajectories_file_name
        self._trajectories_file_name_with_no_fill = trajectories_file_name_with_no_fill
        self._during_time = during_time
    
    def output_characteristics(self):
        adt = 0.0  # average dwell time (s) of vehicles
        adt_std = 0.0  # standard deviation of dwell time (s) of vehicles
        anv = 0.0  # average number of vehicles in each second
        anv_std = 0.0  # standard deviation of number of vehicles in each second
        asv = 0.0  # average speed (m/s) of vehicles
        asv_std = 0.0  # standard deviation of speed (m/s) of vehicles

        df = pd.read_csv(self._trajectories_file_name, names=['vehicle_id', 'time', 'longitude', 'latitude'], header=0)

        vehicle_ids = df['vehicle_id'].unique()
        
        number_of_vehicles_in_seconds = np.zeros(300)
        vehicle_dwell_times = []
        for vehicle_id in vehicle_ids:
            new_df = df[df['vehicle_id'] == vehicle_id]
            vehicle_dwell_time = 0.0
            for row in new_df.itertuples():
                time = getattr(row, 'time')
                x = getattr(row, 'longitude')
                y = getattr(row, 'latitude')
                distance = np.sqrt((x - 1500) ** 2 + (y - 1500) ** 2)
                if distance <= 1500:
                    vehicle_dwell_time += 1.0
                    number_of_vehicles_in_seconds[int(time)] += 1.0
            vehicle_dwell_times.append(vehicle_dwell_time)

        assert len(vehicle_dwell_times) == len(vehicle_ids)
        print("vehicle_number: ", len(vehicle_ids))
        adt = np.mean(vehicle_dwell_times)
        adt_std = np.std(vehicle_dwell_times)

        anv = np.mean(number_of_vehicles_in_seconds)
        anv_std = np.std(number_of_vehicles_in_seconds)

        print("Average dwell time (s):", adt)
        print("Standard deviation of dwell time (s):", adt_std)
        print("Average number of vehicles in each second:", anv)
        print("Standard deviation of number of vehicles in each second:", anv_std)

        vehicle_speeds = []
        df = pd.read_csv(self._trajectories_file_name_with_no_fill, names=['vehicle_id', 'time', 'longitude', 'latitude'], header=0)
        vehicle_ids = df['vehicle_id'].unique()
        for vehicle_id in vehicle_ids:
            vehicle_speed = []
            new_df = df[df['vehicle_id'] == vehicle_id]
            vehicle_dwell_time = 0.0
            last_time = -1.0
            last_x = 0.0
            last_y = 0.0
            for row in new_df.itertuples():
                if int(last_time) == -1:
                    last_time = getattr(row, 'time')
                    last_x = getattr(row, 'longitude')
                    last_y = getattr(row, 'latitude')
                    continue
                time = getattr(row, 'time')
                x = getattr(row, 'longitude')
                y = getattr(row, 'latitude')
                distance = np.sqrt((x - last_x) ** 2 + (y - last_y) ** 2)
                speed = distance / (time - last_time)
                if not np.isnan(speed):
                    vehicle_speed.append(speed)
                last_time = time
                last_x = x
                last_y = y
            if vehicle_speed != []:
                average_vehicle_speed = np.mean(vehicle_speed)
                vehicle_speeds.append(average_vehicle_speed)
        
        asv = np.mean(vehicle_speeds)
        asv_std = np.std(vehicle_speeds)
        print("Average speed (m/s):", asv)
        print("Standard deviation of speed (m/s):", asv_std)