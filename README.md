补光浇水控制器



##### 传感器：

1. ​	土壤湿度传感器（二进制）

2. ​	水位传感器（二进制）

3. ​	光照传感器（值）0-65535lx

   ​	光照传感器(今日累加值)0-93000

##### 开关：

1. ​	LED补光灯
2. ​	水泵
3. ​    自动模式/手动模式



## MQTT定义

​	设备使用mqtt协议进行通讯。

​	HA的MQTT自动发现配置：‘homeassistant/{switch}/{dev_id}/{object_id}/config’

​	由控制台发布，设备端订阅的主题：‘{dev_id}/command’

​	由控制台订阅，设备端发布的主题：‘{dev_id}/state’

#### 自动发现：

###### 1.土壤湿度传感器（binary_sensor）

topic：homeassistant/binary_sensor/{dev_id}/moisture/config

```json
{"device_class": "moisture", "name": "Temperature", "state_topic": "{dev_id}/state", "payload_on": "wet","payload_off":"dry", "value_template": "{{ value_json.moisture_status}}" }
```

###### 2.水位传感器（sensor）

topic：homeassistant/sensor/{dev_id}/water/config

```json
{"device_class": "None", "name": "water", "state_topic": "{dev_id}/state",  "value_template": "{{ value_json.water_level}}" }
```

###### 3.光照传感器（sensor）

topic：homeassistant/sensor/{dev_id}/illuminance/config

```json
{"device_class": "illuminance", "name": "Illuminance", "state_topic": "{dev_id}/state", "unit_of_measurement": "lx", "value_template": "{{ value_json.light_level}}" }
```

###### 3.1光照传感器（累加）

topic：homeassistant/sensor/{dev_id}/exposure/config

```json
{"device_class": "illuminance", "name": "light_accumulation", "state_topic": "{dev_id}/state", "unit_of_measurement": "‰", "value_template": "{{ value_json.light_accumulation}}" }
```

###### 4.LED补光灯（switch）

topic：homeassistant/switch/{dev_id}/led/config

```json
{"name": "plantled", "command_topic": "{dev_id}/led/command","payload_on":"on","payload_off":"off", "state_topic": "{dev_id}/state", "value_template": "{{ value_json.led}}"}
```

###### 5.水泵（switch）

topic：homeassistant/switch/{dev_id}/water/config

```json
{"name": "plantwater", "command_topic": "{dev_id}/water/command","payload_on":"on","payload_off":"off", "state_topic": "{dev_id}/state", "value_template": "{{ value_json.water_pump}}"}
```

###### 6.手工/自动模式切换（switch）

topic：homeassistant/switch/{dev_id}/mode/config

```json
{"name": "devmode", "command_topic": "{dev_id}/mode/command","payload_on":"auto","payload_off":"manual", "state_topic": "{dev_id}/state", "value_template": "{{ value_json.mode}}"}
```



#### 命令主题：

###### 1.控制水泵

topic：{dev_id}/water/command

```json
"on"
"off"
```

###### 2.控制补光灯

topic：{dev_id}/led/command

```json
"on"
"off"
```

###### 3.控制设备工作模式

topic：{dev_id}/dev/command

```json
"auto"
"manual"
```







#### 设备状态：

dev_id:设备id

moisture_status：土壤湿度，true为”干/缺水“，false为”湿润/不缺水“

water_level：水位值浸入水后数值基本在500-600.400以下不敏感

light_level：读取值0-54613

light_accumulation: 当天光照量统计，每10分钟记录一次light_level/1000

led：补光灯是否工作

water_pump:水泵是否工作

###### 1.设备传感器状态

topic：{dev_id}/state

```json
{"dev_id":"9","dev_state":"on","mode":"atuo","moisture_status":"dry","water_level":400,"light_level":10000,"light_accumulation":1930,"led":"on","water_pump":"off"}
{"dev_id":"9","dev_state":"on","mode":"manual","moisture_status":"wet","water_level":400,"light_level":10000,"light_accumulation":1930,"led":"on","water_pump":"off"}
```





```json
"homeassistant/sensor/T0001_Topic01/config";
'{"name":"T0001_Topic01","unit_of_measurement": "dBm","device_class":"signal_strength","state_topic":"homeassistant/sensor/T0001/state","value_template": "{{ value_json.Topic01}}"}'
"homeassistant/sensor/T0001_Topic02/config"
'{"name":"T0001_Topic02","unit_of_measurement": "°C","device_class":"temperature","state_topic":"homeassistant/sensor/T0001/state","value_template": "{{ value_json.Topic02}}"}'

"homeassistant/sensor/T0001/state"
'{"ID":"T0001","Status":"true","Topic01":"-60","Topic02":"25","Topic03":"40","Topic04":"1200"}'

```

