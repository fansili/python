# run.py程序用作启动网站服务
# -*- coding: utf-8 -*-

### 感谢作者（廖雪峰）提供的框架
__author__ = 'Michael Liao'

'''
async web application.  ### 网站开发的框架为aiohttp
'''

# 导入的logging模块用作打印登录日志，（日志级别等级CRITICAL > ERROR > WARNING > INFO > DEBUG > NOTSET）
import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

### 网站开发的框架为aiohttp，前端框架为：jinja2，pip安装
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

### 导入config模块（自定义模块）
from config import configs
### 导入orm（Object Relation Mapping）模块（自定义），封装操作数据库的函数
import orm
### 导入coroweb模块（自定义，封装web核心函数）
from coroweb import add_routes, add_static
### 导入handlers模块（自定义，封装有路由的函数）
from handlers import cookie2user, COOKIE_NAME

### 初始化前端程序jinja2
def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape', True),
        ### 定义block中的代码块
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

### 把一个generator（生成器）标记为coroutine类型，然后就把这个coroutine扔到进程中执行。
### 输出日志：请求方法与请求的文件路径
@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # yield from asyncio.sleep(0.3)  --0.3是指在0.3s之后执行
        # yield from后面的语句会被立即执行
        return (yield from handler(request))
    return logger

### 输出日志：COOKIE_NAME及请求路径
@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth

### 在提交表单时记录请求信息
@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (yield from handler(request))
    return parse_data

### 输出日志：Response handler...
### 对输出的页面进行编码格式，默认UTF-8
@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = yield from handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and t >= 100 and t < 600:
            return web.Response(t)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

### 返回年月日
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

### 网站初始化
@asyncio.coroutine
def init(loop):
	### 与连接池连接，获取数据库配置信息
	#### 不理解loop=loop, **configs.db的含义
    yield from orm.create_pool(loop=loop, **configs.db)
    ### web.application(urls, globals()) 创建一个基于刚提交的URL列表的application
    ### 
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])
    ### 
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    ### 匹配首页路由 ###
    add_routes(app, 'handlers')
    add_static(app)
    srv = yield from loop.create_server(app.make_handler(), '172.18.195.91', 9000)
    logging.info('server started at http://125.70.243.112:8004...')
    return srv

# 把需要执行的线程扔到EventLoop中执行，就实现了异步IO
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))

### 监听网站运行，保持网站在线状态
loop.run_forever()
