
'''
站点配置-封装的有数据库配置操作的函数
'''
### 感谢作者（廖雪峰）提供的框架
__author__ = 'Michael Liao'

### 导入数据库配置
import config_default

### 操作配置的类：Dict
class Dict(dict):
    '''
    Simple dict but support access as x.y style.
    '''
    # 带两个星号（*）参数的函数传入的参数则存储为一个字典（dict）
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

### 覆盖配置信息（不修改原有配置文件，重写配置信息）
def merge(defaults, override):
    r = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                r[k] = merge(v, override[k])
            else:
                r[k] = override[k]
        else:
            r[k] = v
    return r

### 转换格式为Dict
def toDict(d):
    D = Dict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

### 这里的configs是一个对象
configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

### 最终的configs
configs = toDict(configs)
