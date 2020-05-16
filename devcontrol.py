from machine import Pin, Timer, reset, I2C, ADC, RTC
import utime
import network
import bh1750fvi
import ntptime


# 适合用于esp8266 modemcu
# light_id和gpio针脚的定义


class EspDev:
    # mode = esp8266 或者mode = esp32
    def __init__(self, mode='esp8266'):
        if mode == 'esp8266':
            # 时钟初始化
            self.rtc = RTC()
            # 光敏传感器
            # 需要接1-4线，1vcc 4gnd 2scl（D1） 1sda（D2）
            self.i2c = I2C(scl=Pin(5), sda=Pin(4))
            # 水位传感器 （土壤湿度传感器也可用）
            # water sensor A0
            self.adc = ADC(0)
            # 土壤湿度传感器
            # D9（GPIO3）
            self.moisture = Pin(2, Pin.IN)
            self.online = False
            self.water_level = 0
            self.light_level = 0
            self.soil_moisture_status = "wet"
            self.GPIO_MAPPING = {
                'D0': 16,  # D0 GPIO16
                'D4': 2,  # D4 GPIO2
                'D5': 14,  # D5 GPIO14
                'D6': 12,  # D6 GPIO12
                'D7': 13,  # D7 GPIO13
                'D8': 15,  # D8 GPIO15
                'D9': 3,  # D9(RX) GPIO3
                'D10': 1,  # D10(TX) GPIO1
            }

            # 初始状态皆为高电平状态（关灯）
            self.gpio_state = {
                'D0': 1,
                'D4': 0,  # pin为读取，低电平
                'D5': 1,
                'D6': 1,
                'D7': 1,
                'D8': 0,
                'D9': 1,
                'D10': 1,
            }
        else:
            raise NameError("mode={}".format(mode))

        # 初始化时，关闭所有灯
        # self.all_light_off()

    # 水位传感器
    def monitor_water_level(self):
        value = self.adc.read()  # 读取ADC数值 ，浸入水后数值基本在500-600.400以下不敏感
        self.water_level = value
        print(value)
        return value

    # 光敏传感器
    def monitor_light_level(self):
        value = bh1750fvi.sample(self.i2c)
        self.light_level = value
        print(value)  # 读取值0-54613
        return value

    # 土壤湿度传感器(2选1)
    # 传感器A0接口，ADC读取模拟值
    def monitor_soil_moisture(self):
        value = self.adc.read()  # 读取ADC数值 ，断开1024，完全浸入水中最低272
        print(value)
        return value

    # 土壤湿度传感器(2选1)
    # 传感器D0接口，读取高低电平
    # D9（GPIO3）
    # moisture_status = Pin(3,Pin.IN)
    def monitor_soil_moisture_status(self):
        # 读取高低电平，高电平1代表太干，需要加水，低电平0代表湿度达标
        value = self.moisture.value()
        self.soil_moisture_status = "dry" if value else "wet"
        print(self.soil_moisture_status)
        return self.soil_moisture_status

    def ntp_time(self):
        """
        通过ntp服务器同步时间，设备联网后立即同步，之后每12小时同步一次
        :return: 直接作用到设备的RTC
        """
        def sync_ntp(tim):
            ntptime.NTP_DELTA = 3155644800
            ntptime.host = 'ntp1.aliyun.com'
            ntptime.settime()

        sync_ntp(1)
        tim2 = Timer(-1)
        # 每12小时同步一次
        tim2.init(period=3600000 * 12, mode=Timer.PERIODIC, callback=sync_ntp)

    def get_time(self):
        return self.rtc.datetime()

    # 开灯命令，如果hold参数，n秒后自动关灯
    def light_on(self, id, hold=0):
        Pin(self.GPIO_MAPPING[id], Pin.OUT, value=0)
        self.gpio_state[id] = 0
        if hold > 0:
            def lightoff(t):
                self.light_off(id)

            # 开启 RTOS 定时器，编号为-1,一次性，执行定时关灯
            tim1 = Timer(-1)
            tim1.init(period=1000 * hold, mode=Timer.ONE_SHOT, callback=lightoff)

    def light_off(self, id):
        Pin(self.GPIO_MAPPING[id], Pin.OUT, value=1)
        self.gpio_state[id] = 1

    def led_switch(self, action='on'):
        """
        led补光灯的开关位于D10（gpio1）
        :param action:‘on’ or 'off'
        :return:
        """
        self.light_on('D10') if action == 'on' else self.light_off('D10')

    def get_led_switch(self):
        # 低电平表示开??
        return 'off' if self.gpio_state['D10'] else 'on'

    def water_pump(self, action='on'):
        #  同led_switch()
        self.light_on('D9') if action == 'on' else self.light_off('D9')

    def get_water_pump(self):
        # 低电平表示开??
        return 'off' if self.gpio_state['D9'] else 'on'

    def light_state(self, id):
        return self.gpio_state[id]

    def all_light_state(self):
        return self.light_state

    def all_light_on(self):
        for light_id, light_state in self.gpio_state.items():
            if light_state:
                self.light_on(light_id)

    def all_light_off(self):
        for light_id, light_state in self.gpio_state.items():
            if not light_state:
                self.light_off(light_id)

    def dev_restart(self):
        reset()

    def wifi_connect(self, ssid, wifipwd):
        # 初始化 WIFI 指示灯
        WIFI_LED = 'D4'
        # STA 模式
        wlan = network.WLAN(network.STA_IF)
        # 激活接口
        wlan.active(True)
        # 记录时间做超时判
        start_time = utime.time()

        if not wlan.isconnected():
            wlan.connect(ssid, wifipwd)

            while not wlan.isconnected():
                # LED闪烁
                self.light_on(WIFI_LED)
                utime.sleep_ms(300)
                self.light_off(WIFI_LED)
                utime.sleep_ms(300)

                # 超时判断,30 秒没连接成功判定为超时
                if utime.time() - start_time > 30:
                    print('WIFI Connected Timeout!')
                    print('Restart Now!')
                    self.dev_restart()

        if wlan.isconnected():
            # LED 点亮
            self.light_on(WIFI_LED)
            self.online = True
            # 串口打印信息
            wlan_ifconfig = wlan.ifconfig()
            print('network info:', wlan_ifconfig)
            # OLED 数据显示
            # 清屏背景黑色
            print('IP/Subnet/GW:')
            print(wlan.ifconfig()[0])
            print(wlan.ifconfig()[1])
            print(wlan.ifconfig()[2])
            # 同步ntptime
            self.ntp_time()
            print(self.get_time())
            return wlan
        else:
            return False


if __name__ == '__main__':
    print("espdevcontrol testing")
    mydev = EspDev("esp8266")
    mydev.light_on(4, 5)

# from machine import RTC
# import time
# import ntptime
# import network
#
# class Esp:
#     def __init__(self):
#         self.rtc = RTC()
#
#     def get_time(self):
#         ntptime.settime()
#
#     def wifi(self):
#         wlan = network.WLAN(network.STA_IF)
#         # 激活接口
#         wlan.active(True)
#         wlan.connect('PandoraBox', 'zld123456')
#         print(wlan.ifconfig())
