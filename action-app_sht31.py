#!/usr/bin/env python3
import time

from hermes_python.hermes import Hermes
from hermes_python.ontology import MqttOptions
import smbus2

import snips_common


class SensorError(Exception):
    pass


class BaseSht31Action(snips_common.ActionWrapper):
    reactions = {SensorError: "Désolée, je n'ai pas de réponse des capteurs."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bus = smbus2.SMBus(1)

    def get_temperature_humidity(self, ret='temperature'):
        try:
            self.bus.write_i2c_block_data(0x44, 0x2C, [0x06])
            time.sleep(0.2)
            data = self.bus.read_i2c_block_data(0x44, 0x00, 6)
        except IOError as exc:
            print("[Error] No sensor found")
            raise SensorError from exc

        temp = data[0] * 256 + data[1]
        cTemp = -45 + (175 * temp / 65535.0)
        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

        if ret == 'temperature':
            return cTemp
        if ret == 'humidity':
            return humidity


class ActionTemperature(BaseSht31Action):
    def action(self):
        if not self.message_for_this_site():
            return

        temp = round(self.get_temperature_humidity('temperature'), 1)
        print("Celsius:", temp, "°C")

        self.end_session(
            "Il fait actuellement",
            snips_common.french_number(temp, 1),
            "degrés"
        )


class ActionHumidity(BaseSht31Action):
    def action(self):
        if not self.message_for_this_site():
            return

        humidity = round(self.get_temperature_humidity('humidity'), 1)
        print("Humidity:", humidity, "%")

        self.end_session(
            "L'humidité est de", snips_common.french_number(humidity, 1), "%"
        )


if __name__ == "__main__":
    mqtt_opts = MqttOptions()

    with Hermes(mqtt_options=mqtt_opts) as hermes:
        hermes.subscribe_intent('checkTemperature', ActionTemperature.callback)
        hermes.subscribe_intent('checkHumidity', ActionHumidity.callback)
        hermes.start()
