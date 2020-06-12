config = {
    # dev_id=3
    "dev_id": "10",
    "dev_mode": "esp32",
    # "dev_mode": "esp8266",
    "ssid": "PandoraBox",
    "wifipwd": "zld123456",
    "mqtt_broker": "192.168.10.90",
    "mqtt_port": 1883,
    "mqtt_user": "mqtt",
    "mqtt_pwd": "mqtt",
    "mqtt_client_id": "esp32-10-plant",
    # 默认工作模式为自动模式
    "mode": "auto",
    # mode : manual,
    # 每天开始补光的时间,
    "led_start_time": "15:00",
    # 每天必须结束补光的时间,
    "led_stop_time": "20:00",
    # 光照期望值。即光量达到多少后关灯
    "light_accumulation_target": 2000,
    # webrepl_password=123456789
    # 水箱最低水位值0-4095（低于该值水泵不工作）
    "min_water_level": 0
}
