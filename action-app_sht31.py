#!/usr/bin/env python3
import traceback

from hermes_python.hermes import Hermes
from hermes_python.ontology import MqttOptions
import time
import smbus2


def subscribe_intent_callback(hermes, intent_message):
    action_wrapper = ActionWrapper(hermes, intent_message)
    try:
        action_wrapper.action()
    except SensorError:
        action_wrapper.say("Désolée, je n'ai pas de réponse des capteurs.")
    except Exception:
        traceback.print_exc()
        action_wrapper.say("Désolée, il y a eu une erreur.")


def french_number(number):
    number = float(number)
    if int(number) == number:
        number = int(number)
    return str(number).replace(".", ",")


class SensorError(Exception):
    pass


class ActionWrapper:
    def __init__(self, hermes, intent_message):
        self.hermes = hermes
        self.intent_message = intent_message
        self.site_id = 'default'  # TODO
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

    def askTemperature(self):
        temp = round(self.get_temperature_humidity('temperature'), 1)
        print("Celsius:", temp, "°C")

        self.say("Il fait actuellement", french_number(temp), "degrés")

    def askHumidity(self):
        humidity = round(self.get_temperature_humidity('humidity'), 1)
        print("Humidity:", humidity, "%")

        self.say("L'humidité est de", french_number(humidity), "%")

    def action(self):
        if self.intent_message.site_id != self.site_id:
            return
        if self.intent_message.intent.intent_name == 'checkTemperature':
            self.askTemperature()
        if self.intent_message.intent.intent_name == 'checkHumidity':
            self.askHumidity()

    def say(self, message, *args):
        current_session_id = self.intent_message.session_id
        message = message + " " + " ".join(args)
        self.hermes.publish_end_session(current_session_id, message)


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intent('checkTemperature', subscribe_intent_callback)
        h.subscribe_intent('checkHumidity', subscribe_intent_callback)
        h.start()
