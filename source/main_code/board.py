import os
import glob
import time

import serial
import serial.tools.list_ports

from sensor import Sensor


class Board:
    MEASURE = "m"
    CONNECT_SENSOR = "c"
    DISCONNECT_SENSOR = "d"

    MAX_VOLTAGE = 5
    MAX_SENSOR_VALUE = 1024
    RESISTOR_RESISTANCE = 1000

    boards_list = []

    @staticmethod
    def update_boards_list():
        Board.disconnect_boards()
        is_windows = str(os.name).lower() == 'nt'

        if is_windows:
            ports = serial.tools.list_ports.comports()
        else:
            ports = glob.glob('/dev/tty[UA][A-Za-z]*')

        board_index = 0
        for port in ports:
            try:
                if is_windows:
                    port_name = port.name
                else:
                    port_name = port

                s = serial.Serial(port_name)
                s.close()
                Board.boards_list.append(Board(board_index, port_name))
                board_index += 1
            except (OSError, serial.SerialException):
                pass

    @staticmethod
    def disconnect_boards():
        for board in Board.boards_list:
            board.port.close()
        Board.boards_list = []

    @staticmethod
    def connect_sensor(sensor_name):
        sensor = Board.find_sensor_by_name(sensor_name)
        if sensor and not sensor.connected_status:
            port_message = f'{Board.CONNECT_SENSOR}{sensor.pin_index}'
            sensor.board.write_line(port_message)
            sensor.connect()

    @staticmethod
    def disconnect_sensor(sensor_name):
        sensor = Board.find_sensor_by_name(sensor_name)
        if sensor and sensor.connected_status:
            port_message = f'{Board.DISCONNECT_SENSOR}{sensor.pin_index}'
            sensor.board.write_line(port_message)
            sensor.disconnect()

    @staticmethod
    def rename_sensor(sensor_name_old, sensor_name_new):
        sensor = Board.find_sensor_by_name(sensor_name_old)
        if sensor and not Board.find_sensor_by_name(sensor_name_new):
            sensor.rename(sensor_name_new)

    @staticmethod
    def find_sensor_by_name(sensor_name):
        for board in Board.boards_list:
            for sensor in board.sensors_list:
                if sensor.get_name() == sensor_name:
                    return sensor
        return False

    @staticmethod
    def get_all_connected_sensors():
        sensors_list = []
        for board in Board.boards_list:
            sensors_list += board.get_connected_sensors()
        return sensors_list

    @staticmethod
    def measure_all_boards():
        for board in Board.boards_list:
            board.measure()

    @staticmethod
    def get_temperature_by_pin_value(sensor_value):
        sensor_voltage =\
            Board.MAX_VOLTAGE * sensor_value / Board.MAX_SENSOR_VALUE
        sensor_resistance =\
            Board.RESISTOR_RESISTANCE * sensor_voltage /\
            (Board.MAX_VOLTAGE - sensor_voltage)
        return 100 / 385 * sensor_resistance - 100000 / 385

    def __init__(self, board_index, port_name):
        print(board_index, port_name)
        time.sleep(3)
        self.device_name = f'board-{board_index + 1}'
        self.port = serial.Serial(port_name, 9600, timeout=1)
        self.sensors_list = []
        input_pins_number = int(self.read_line())
        self.generate_sensors_list(input_pins_number)

    def generate_sensors_list(self, input_pins_number):
        self.sensors_list = []
        for input_pin_index in range(0, input_pins_number):
            sensor = Sensor(self, input_pin_index)
            self.sensors_list.append(sensor)

    def get_all_sensors_number(self):
        return len(self.sensors_list)

    def get_connected_sensors_number(self):
        connected_sensors_number = 0
        for sensor in self.sensors_list:
            if sensor.connected_status:
                connected_sensors_number += 1
        return connected_sensors_number

    def get_connected_sensors(self):
        connected_sensors = []
        for sensor in self.sensors_list:
            if sensor.get_connected_status():
                connected_sensors.append(sensor)
        return connected_sensors

    def measure(self):
        self.write_line(Board.MEASURE)
        connected_pins_values = self.read_line().split(' ')
        for i, sensor in enumerate(self.get_connected_sensors()):
            pin_value = int(connected_pins_values[i])
            temperature = Board.get_temperature_by_pin_value(pin_value)
            sensor.set_value(temperature)

    def write_line(self, data):
        self.port.write(data.encode())

    def read_line(self):
        while True:
            if self.port.in_waiting:
                return self.port.readline().decode('utf-8').strip('\n\r')
