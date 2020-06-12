from machine import Timer
from simple import MQTTClient
from devcontrol32 import EspDev
import time
import json
import espconf

# 读取配置文件
config = espconf.config
DEVICE_ID = config['dev_id']
work_mode = config['mode']
# 光照总量
light_total = 0
# io错误计数器
oserror_counter = 0
# 期待光照
LIGHT_ACCUMULATION_TARGET = config['light_accumulation_target']
esp = EspDev()
esp.wifi_connect(ssid=config['ssid'], wifipwd=config['wifipwd'])
# 水箱最低水位
MIN_WATER = config['min_water_level']
# 指示灯
# 缺水指示灯
RED_LED = 'P19'
# 水泵工作
GREEN_LED = 'P18'

if esp.online:
    print("联网状态运行")


def water_mod(moisture_status, water_level):
    print("INFO:water_mod start")
    print("INFO:moisture_status:%s,water_level:%s" % (moisture_status, water_level))
    # 缺水指示灯动作
    esp.light_on(RED_LED) if water_level <= MIN_WATER else esp.light_off(RED_LED)

    water_pump_state = esp.get_water_pump()
    print("INFO:water_pump_state:%s" % water_pump_state)
    # 水泵动作
    if moisture_status == "dry" and water_level > MIN_WATER and water_pump_state == "off":
        print("INFO:water pump will start")
        # 缺水  and 水箱有水  and 水泵未工作
        # 水泵工作指示灯(绿灯)
        esp.light_on(GREEN_LED)
        # 启动水泵
        esp.water_pump('on')
    elif moisture_status == "wet" or water_level < MIN_WATER and water_pump_state == "on":
        print("INFO:water pump will stop")
        esp.light_off(GREEN_LED)
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
        # light_total += int(light_level / 1000)
        light_total += light_level

    def to_minutes(hm):
        return int(hm[0]) * 60 + int(hm[1])

    led_start_time = to_minutes(config['led_start_time'].split(":"))
    led_stop_time = to_minutes(config['led_stop_time'].split(":"))
    now_time = to_minutes(datetime[4:6])

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
    elif esp.get_led_switch() == "on":
        print("INFO:will stop led out time")
        esp.led_switch("off")
    print("INFO:success light_mod")


def cron_main(tim1=0):
    global oserror_counter
    # 定期检查mqtt订阅
    print("INFO:go to check msg")
    try:
        client.check_msg()
        oserror_counter = 0
        print("INFO:success check msg")
    except Exception as e:
        oserror_counter += 1
        print("ERROR:%s" % e)
        print("ERROR:check_msg is error!oserror_counter:%s" % oserror_counter)
        if oserror_counter >= 30:
            esp.dev_restart()

    # 土壤干湿度检测
    moisture_status = esp.monitor_soil_moisture_status()
    # 水位检测
    water_level = esp.monitor_water_level()
    # 光照检测
    light_level = esp.monitor_light_level()
    if work_mode == "auto":
        water_mod(moisture_status, water_level)
        light_mod(light_level)


def mqtt_send(tims=0):
    # 定期发送的信息
    print("INFO:go to send mqtt")
    data = json.dumps({"dev_id": DEVICE_ID,
                       "dev_state": "on",
                       "mode": work_mode,
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
    topic = topic.decode()
    msg = msg.decode()
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
            esp.light_on(GREEN_LED)
            # 启动水泵
            esp.water_pump('on')
        else:
            esp.light_off(GREEN_LED)
            esp.water_pump('off')
    elif "led" in topic:
        work_mode = 'manual'
        if msg == "on":
            # 打开补光灯
            esp.led_switch("on")
        else:
            esp.led_switch("off")
    elif "mode" in topic:
        work_mode = "manual" if msg == "manual" else "auto"
    # 主动发送变化状态
    mqtt_send()


def my_mqtt_pulish(topic, data):
    try:
        client.publish(topic, data)
        time.sleep_ms(200)
        print("INFO:publish success topic : %s" % topic)
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
    state_topic = DEVICE_ID + "/devstate"
    # 1 土壤湿度传感器（binary_sensor）
    my_mqtt_pulish("homeassistant/binary_sensor/{}/moisture/config".format(DEVICE_ID),
                   json.dumps(
                       {"device_class": "moisture", "name": "plant_moisture" + DEVICE_ID, "state_topic": state_topic,
                        "payload_on": "wet",
                        "payload_off": "dry",
                        "value_template": "{{ value_json.moisture_status}}"})
                   )
    # 2 水位传感器（sensor）
    my_mqtt_pulish("homeassistant/sensor/{}/water/config".format(DEVICE_ID),
                   json.dumps({"name": "plant_water" + DEVICE_ID, "state_topic": state_topic,
                               "value_template": "{{ value_json.water_level}}"})
                   )
    # 3 光照传感器（sensor）
    my_mqtt_pulish("homeassistant/sensor/{}/illuminance/config".format(DEVICE_ID),
                   json.dumps({"device_class": "illuminance", "name": "plant_Illuminance" + DEVICE_ID,
                               "state_topic": state_topic,
                               "unit_of_measurement": "lx", "value_template": "{{ value_json.light_level}}"})
                   )
    # 3.1 光照传感器（累加）
    my_mqtt_pulish("homeassistant/sensor/{}/exposure/config".format(DEVICE_ID),
                   json.dumps(
                       {"device_class": "illuminance", "name": "light_total" + DEVICE_ID, "state_topic": state_topic,
                        "unit_of_measurement": "lx", "value_template": "{{ value_json.light_accum}}"})
                   )
    # 4.LED补光灯（switch）
    my_mqtt_pulish("homeassistant/switch/{}/led/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_led" + DEVICE_ID, "command_topic": DEVICE_ID + "/led/command",
                        "payload_on": "on",
                        "payload_off": "off", "state_topic": state_topic, "value_template": "{{ value_json.led}}"})
                   )
    # 5.水泵（switch）
    my_mqtt_pulish("homeassistant/switch/{}/waterpump/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_waterpump" + DEVICE_ID, "command_topic": DEVICE_ID + "/water/command",
                        "payload_on": "on",
                        "payload_off": "off", "state_topic": state_topic,
                        "value_template": "{{ value_json.water_pump}}"})
                   )
    # 6.手工/自动模式切换（switch）
    my_mqtt_pulish("homeassistant/switch/{}/mode/config".format(DEVICE_ID),
                   json.dumps(
                       {"name": "plant_devmode" + DEVICE_ID, "command_topic": DEVICE_ID + "/mode/command",
                        "payload_on": "auto",
                        "payload_off": "manual", "state_topic": state_topic, "value_template": "{{ value_json.mode}}"})
                   )


def mqtt_connect():
    # mqtt初始化
    print("mqtt_broker:%s" % config['mqtt_broker'])
    client = MQTTClient(client_id=config['mqtt_client_id'],
                        server=config['mqtt_broker'],
                        port=config['mqtt_port'],
                        user=config['mqtt_user'],
                        password=config['mqtt_pwd'],
                        keepalive=120)
    # 设置mqtt订阅回调
    client.set_callback(mqtt_callback)
    # 设置遗言
    # 向主题/{dev_id}/devstate ，发送{"dev_id":2,"dev_state":"offline"}
    last_will = json.dumps({"dev_id": DEVICE_ID, "dev_state": 'off'})
    client.set_last_will(DEVICE_ID + '/devstate', last_will)
    return client


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

# 检查订阅 传感器刷新
if config['dev_mode'] == 'esp8266':
    print("INFO:dev_mode is esp8266")
    # 定期发送状态
    tims = Timer(-1)
    tims.init(period=1000 * 30, mode=Timer.PERIODIC, callback=mqtt_send)
    # 开启 RTOS 定时器，编号为-1,周期 1000ms，执行MQTT订阅任务
    tim1 = Timer(-1)
    tim1.init(period=3000, mode=Timer.PERIODIC, callback=cron_main)
elif config['dev_mode'] == 'esp32':
    # 使用多线程执行MQTT订阅任务
    print("INFO:dev_mode is esp32")
    import _thread


    def cron_main_thread():
        while True:
            cron_main()
            time.sleep_ms(2000)


    def mqtt_send_thread():
        while True:
            mqtt_send()
            time.sleep_ms(30000)


    _thread.start_new_thread(cron_main_thread, ())
    _thread.start_new_thread(mqtt_send_thread, ())
