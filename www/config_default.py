### 配置数据库信息

'''
Mysql数据库的配置信息（如需修改，请在config_override.py处修改）
'''
configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'db': 'mysql'
    },
    'session': {
        'secret': 'Awesome'
    }
}
