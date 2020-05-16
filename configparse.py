'''
通过读取文本文件，解析返回dict类型
dev_id=2
light_id=2
command=0
client_id=esp826602
ssid=xiaov
passwd=xiaov1234
ip=192.168.100.15
'''


class ConfigParse:
    def __init__(self, path):
        self.path = path

    def read_config(self):
        with open(self.path, 'r') as f:
            config_list = f.readlines()
        config_dict = {}
        for config in config_list:
            config = config.strip()
            if len(config)>0 and config[0] == '#':
                continue
            config_sp = config.split("=", 1)
            if len(config_sp) > 1:
                config_dict[config_sp[0].strip()] = config_sp[1].strip().replace('\n', '').replace('\r', '')
        return config_dict


if __name__ == '__main__':
    cp = ConfigParse("esppy.conf")
    print(cp.read_config())
