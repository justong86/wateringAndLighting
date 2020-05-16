from machine import Timer
from simple import MQTTClient
from configparse import ConfigParse
from devcontrol import EspDev
import time
import json

# 读取配置文件
config = ConfigParse('esp.conf').read_config()
DEVICE_ID = config['dev_id']
work_mode = config['mode']
# 光照总量
light_total = 0
# 期待光照
LIGHT_ACCUMULATION_TARGET = int(config['light_accumulation_target'])
esp = EspDev()
esp.wifi_connect(ssid=config['ssid'], wifipwd=config['wifipwd'])
if esp.online:
    print("联网状态运行")


def water_mod(moisture_status, water_level):
    print("INFO:water_mod start")
    # 缺水指示灯动作
    esp.light_on('D7') if water_level else esp.light_off('D7')
    # 水泵动作
    if moisture_status == "dry" and water_level > 100 and esp.get_water_pump() == "off":
        # 缺水  and 水箱有水  and 水泵未工作
        # 水泵工作指示灯(绿灯)
        esp.light_on('D8')
        # 启动水泵
        esp.water_pump('on')
    elif esp.get_water_pump() == "on":
        esp.light_off('D8')
        esp.water_pump('off')
    print("INFO:success water_mod")


def light_mod(light_level):
    print("INFO:light_mod start")
    global light_total
    # （年，月，日，星期，时，分，秒，微秒）
    datetime = esp.get_time()
    # 每天0时重置光量
    if datetime[4:7] == (0, 0, 0):
        light_total = 0
    # 每10分钟记录一次
    if datetime[6] == 0 and datetime[5] % 10 == 0:
        light_total += int(light_level / 1000)

    def to_minutes(hm):
        return int(hm[0]) * 60 + int(hm[1])

    led_start_time = to_minutes(config['led_start_time'].split(":"))
    led_stop_time = to_minutes(config['led_stop_time'].split(":"))
    now_time = to_minutes(datetime[4:6])

    print("INFO:will judge light in time?")
    # 只在设定时间范围内控制灯，其他时间关灯
    if led_start_time <= now_time < led_stop_time:
        # 动态时间法：到达设定开灯时间后，开灯，直到光量达到期望值，关灯（忽略led_base_time）
        print("INFO:judge light in time")
        # led_state = esp.get_led_switch()
        led_state = "off"
        print("INFO:led_state:%s" % led_state)
        if light_total < LIGHT_ACCUMULATION_TARGET and led_state == "off":
            # 光照未达到期望值 and 灯是关的
            print("INFO:will start led")
            esp.led_switch("on")
        elif light_total >= LIGHT_ACCUMULATION_TARGET and led_state == "on":
            # 光照已经达到期望值 and 灯是开的
            print("INFO:will stop led in time")
            esp.led_switch("off")
        print("light in the time")
    elif esp.get_led_switch() == "on":
        print("INFO:will stop led out time")
        esp.led_switch("off")
    print("INFO:success light_mod")


def cron_main(tim1):
    # 定期检查mqtt订阅
    print("INFO:go to check msg")
    # client.check_msg()
    print("INFO:success check msg")
    # 土壤干湿度检测
    moisture_status = esp.monitor_soil_moisture_status()
    # 水位检测
    water_level = esp.monitor_water_level()
    # 光照检测
    light_level = esp.monitor_light_level()
    # if work_mode == "auto":
    #     water_mod(moisture_status, water_level)
    #     light_mod(light_level)


def mqtt_send(tims):
    # 定期发送的信息
    print("INFO:go to send mqtt")
    data = json.dumps({"dev_id": DEVICE_ID,
                       "dev_state": "on",
                       "moisture_status": esp.soil_moisture_status,
                       "water_level": esp.water_level,
                       "light_level": esp.light_level,
                       "light_accum": light_total,
                       "led": esp.get_led_switch(),
                       "water_pump": esp.get_water_pump()
                       })
    try:
        my_mqtt_pulish(DEVICE_ID + '/devstate', data)
    except OSError as e:
        print("mqtt_send:%s" % e)
        # esp.dev_restart()
    print("INFO:success send mqtt")


# mqtt订阅收到消息后的回调方法
def mqtt_callback(topic, msg):
    # recive_mes = json.loads(msg)
    # print(recive_mes)
    print("funcation:mqtt_callback")
    print("sub_topic:%s" % topic)
    print("sub_msg:%s" % msg)
    """
    1.自动模式 "command":"auto"
    2.开灯 "command":"led_on"
    3.关灯 "command":"led_off"
    4.打开水泵"command":"water_dump_on"
    5.关闭水泵"command":"water_dump_off"
    """
    global work_mode
    # 1.开灯 "command":"light_on"
    if "water" in topic:
        work_mode = 'manual'
        if msg == "on":
            # 水泵工作指示灯(绿灯)
            esp.light_on('D8')
            # 启动水泵
            esp.water_pump('on')
        else:
            esp.light_off('D8')
            esp.water_pump('off')
    if "led" in topic:
        work_mode = 'manual'
        if msg == "on":
            # 打开补光灯
            esp.led_switch("on")
        else:
            esp.led_switch("off")
    if "mode" in topic:
        work_mode = "manual" if msg == "manual" else "auto"


def my_mqtt_pulish(topic, data):
    try:
        client.publish(topic, data)
    except OSError as e:
        print(e)
        time.sleep_ms(1000)


def ha_discover():
    # 利用HA的自动发现功能，注册设备
    """
        1.土壤湿度传感器（binary_sensor）
        topic：homeassistant / binary_sensor / {dev_id} / moisture / config
        2.水位传感器（sensor）
        topic：homeassistant/sensor/{dev_id}/water/config
        3.光照传感器（sensor）
        topic：homeassistant/sensor/{dev_id}/illuminance/config
        3.1光照传感器（累加）
        topic：homeassistant/sensor/{dev_id}/exposure/config
        4.LED补光灯（switch）
        topic：homeassistant/switch/{dev_id}/led/config
        5.水泵（switch）
        topic：homeassistant/switch/{dev_id}/water/config
        6.手工/自动模式切换（switch）
        topic：homeassistant/switch/{dev_id}/mode/config
    """
    state_topic = DEVICE_ID + "/state"
    # 1 土壤湿度传感器（binary_sensor）
    my_mqtt_pulish("homeassistant/binary_sensor/{}/moisture/config".format(DEVICE_ID),
                   json.dumps({"device_class": "moisture", "name": "plant_Temperature", "state_topic": state_topic,
                               "payload_on": "wet",
                               "payload_off": "dry",
                               "value_template": "{{ value_json.moisture_status}}"})
                   )
    print("INFO:publish 1 success")
    time.sleep_ms(200)
    # 2 水位传感器（sensor）
    my_mqtt_pulish("homeassistant/sensor/{}/water/config".format(DEVICE_ID),
                   json.dumps({"device_class": "None", "name": "plant_water", "state_topic": state_topic,
                               "value_template": "{{ value_json.water_level}}"})
                   )
    print("INFO:publish 2 success")
    time.sleep_ms(200)
    # 3 光照传感器（sensor）
    my_mqtt_pulish("homeassistant/sensor/{}/illuminance/config".format(DEVICE_ID),
                   json.dumps({"device_class": "illuminance", "name": "plant_Illuminance", "state_topic": state_topic,
                               "unit_of_measurement": "lx", "value_template": "{{ value_json.light_level}}"})
                   )
    print("INFO:publish 3 success")
    time.sleep_ms(200)
    # 3.1 光照传感器（累加）
    my_mqtt_pulish("homeassistant/sensor/{}/exposure/config".format(DEVICE_ID),
                   json.dumps({"device_class": "illuminance", "name": "light_total", "state_topic": state_topic,
                               "unit_of_measurement": "Q", "value_template": "{{ value_json.light_accum}}"})
                   )
    print("INFO:publish 3.1 success")
    time.sleep_ms(200)
    # 4.LED补光灯（switch）
    my_mqtt_pulish("homeassistant/switch/{}/led/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_led", "command_topic": DEVICE_ID + "/led/command", "payload_on": "on",
                        "payload_off": "off", "state_topic": state_topic, "value_template": "{{ value_json.led}}"})
                   )
    time.sleep_ms(200)
    print("INFO:publish 4 success")
    # 5.水泵（switch）
    my_mqtt_pulish("homeassistant/switch/{}/water/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_water", "command_topic": DEVICE_ID + "/water/command", "payload_on": "on",
                        "payload_off": "off", "state_topic": state_topic,
                        "value_template": "{{ value_json.water_pump}}"})
                   )
    time.sleep_ms(200)
    print("INFO:publish 5 success")
    # 6.手工/自动模式切换（switch）
    my_mqtt_pulish("homeassistant/switch/{}/mode/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_devmode", "command_topic": DEVICE_ID + "/mode/command", "payload_on": "auto",
                        "payload_off": "manual", "state_topic": state_topic, "value_template": "{{ value_json.mode}}"})
                   )
    time.sleep_ms(200)
    print("INFO:publish 6 success")
    time.sleep_ms(200)
    my_mqtt_pulish("homeassistant/test/good", json.dumps({"state": "good"}))
    print("INFO:publish 7 success")


def mqtt_connect():
    # mqtt初始化
    print("mqtt_broker:%s" % config['mqtt_broker'])
    client = MQTTClient(client_id=config['mqtt_client_id'],
                        server=config['mqtt_broker'],
                        port=int(config['mqtt_port']),
                        user=config['mqtt_user'],
                        password=config['mqtt_pwd'],
                        keepalive=120)
    # 设置mqtt订阅回调
    client.set_callback(mqtt_callback)
    # 设置遗言
    # 向主题/{dev_id}/devstate ，发送{"dev_id":2,"dev_state":"offline"}
    last_will = json.dumps({"dev_id": DEVICE_ID, "dev_state": 'off'})
    client.set_last_will(DEVICE_ID + '/state', last_will)
    return client

def test_fun():
    print("DEBUG::::test_fun()")

client = mqtt_connect()
print("INFO:get clinet success")
client.connect()
print("INFO:connect clinet success")
# 订阅主题{dev_id}/+/command'
client.subscribe(DEVICE_ID + '/+/command')
print("INFO:subscribe success")
# 向HA的自动发现功能注册设备组件
ha_discover()
print("INFO:public discovery success")
# 定期发送状态
tim1 = Timer(-1)
tim1.init(period=3000, mode=Timer.PERIODIC, callback=test_fun)
# 检查订阅 传感器
# tims = Timer(-1)
# tims.init(period=1000 * 30, mode=Timer.PERIODIC, callback=mqtt_send)
# counter = 0
# while True:
#     counter += 1
#     if counter // 5 == 0:
#         cron_main(1)
#     if counter >= 6:
#         mqtt_send(1)
#         counter = 0
#     time.sleep_ms(1000)
