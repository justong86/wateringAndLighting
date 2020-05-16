config = {
    # dev_id=3
    "dev_id": 9,
    # dev_mode=esp32,
    "dev_mode": "esp8266",
    "ssid": "PandoraBox",
    "wifipwd": "zld123456",
    "mqtt_broker": "192.168.10.90",
    "mqtt_port": 1883,
    "mqtt_user": "mqtt",
    "mqtt_pwd": "mqtt",
    "mqtt_client_id": "esp8266-9-plant",
    "mode": "auto",
    # mode = manual,
    # 每天开始补光的时间,
    "led_start_time": "15:00",
    # 每天必须结束补光的时间,
    "led_stop_time": "20:00",
    # 光照期望值（2选1）。即光量达到多少后关灯
    "light_accumulation_target": 2000,
    # 基础光照（2选1）。即每天至少补光多少分钟
    # led_base_time= 120
}
