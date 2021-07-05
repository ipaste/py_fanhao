#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging;logging.basicConfig(format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',level=logging.INFO)
import os
import shutil

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import searcher
from Base import (APP_PATH, PHOTO_PATH, STATIC_PATH, Pager, getconfig, json,
                  jsonres)
from models import db, fanhao

routes = web.RouteTableDef()

__author__ = 'william'

env = Environment(loader=FileSystemLoader(os.path.join(APP_PATH, 'templates')))


def render(tempname, *args, **kwargs):
    template = env.get_template(tempname)
    html = template.render(*args, **kwargs)
    return html


@routes.get('/')
async def index(request):
    print(request.query)
    requestdata = {}
    pageindex = 1
    if 'pageindex' in request.query and request.query['pageindex']:
        pageindex = int(request.query['pageindex'])
    requestdata['pageindex'] = pageindex

    pagesize = 15
    if 'pagesize' in request.query and request.query['pagesize']:
        pagesize = int(request.query['pagesize'])
    requestdata['pagesize'] = pagesize

    ps = fanhao.select()

    if 'downed' in request.query and request.query['downed']:
        downed = request.query['downed']
        ps = ps.where(fanhao.downed == downed)
        requestdata['downed'] = downed

    if 'code' in request.query and request.query['code']:
        code = request.query['code']
        ps = ps.where(fanhao.code == code)
        requestdata['code'] = code

    if 'ma' in request.query and request.query['ma']:
        ma = request.query['ma']
        if ma == '0' or ma == '1' or ma == '2':
            ps = ps.where(fanhao.ima == ma)
            requestdata['ma'] = ma

    if 'star' in request.query and request.query['star']:
        star = request.query['star']
        if star == '-1':
            star = ''
        ps = ps.where(fanhao.star == star)
        requestdata['star'] = star

    count = ps.count()

    allcode = fanhao.select(fanhao.code).order_by(fanhao.code.asc())
    allstar = fanhao.select(fanhao.star).group_by(fanhao.star)
    ps = ps.order_by(fanhao.id.desc()).paginate(pageindex, pagesize)
    pager = Pager(count, pageindex, pagesize)
    html = render('index.html', {'allcode': allcode, 'allstar': allstar, 'ps': ps, 'requestdata': requestdata,'dbweb':getconfig('dbweb','url'), 'pagehtml': pager.render()})
    db.close()
    return web.Response(body=bytes(html, encoding="utf-8"), content_type='text/html')


@routes.get('/search')
async def search(request):
    if 'xcode' not in request.query:
        return jsonres(0)
    xcode = request.query['xcode']
    try:
        ps = fanhao.get(fanhao.code == xcode)
        return jsonres(-1, '已存在', ps.code)
    except fanhao.DoesNotExist:
        pass

    res = await searcher.getinfo(xcode)
    if res['code'] == 0:
        return jsonres(0, '获取成功', res['data'])
    elif res['code'] == -4 or res['code'] == -5:
        return jsonres(-2, '获取图片失败,请稍后重新获取图片')
    else:
        return jsonres(-3, '获取失败:' + res['msg'], res['data'])


@routes.get('/recode')
async def recode(request):
    if 'xcode' not in request.query:
        return jsonres(-1, 'xcode err')
    xcode = request.query['xcode']

    res = await searcher.getinfo(xcode, True)
    if res['code'] == 0:
        return jsonres(0, '重新获取成功', res['data'])
    else:
        return jsonres(-1, '重新获取失败:' + res['msg'])


@routes.get('/set/{type}/{id}/{val}')
async def set(request):
    type = request.match_info.get('type')
    id = request.match_info.get('id')
    val = request.match_info.get('val')
    if not type or not id or not val:
        return jsonres(1, 'args err')
    try:
        f = fanhao.get(fanhao.id == id)
        if type == 'starnum':
            f.starnum = int(val)
        if type == 'downed':
            f.downed = int(val)
        if type == 'iface':
            f.iface = int(val)
        if type == 'ima':
            f.ima = int(val)
        f.save()
        db.close()
        return jsonres(0, 'ok')
    except fanhao.DoesNotExist:
        return jsonres(1, 'not exist')


@routes.get('/deimg')
async def deimg(request):

    if 'pid' not in request.query:
        return jsonres(-1, 'pid err')

    pid = request.query['pid']

    try:
        rs = fanhao.get(fanhao.id == pid)
        rs.delete_instance()
        if os.path.exists(os.path.join(PHOTO_PATH, rs.code + '.jpg')):
            os.remove(os.path.join(PHOTO_PATH, rs.code + '.jpg'))
        db.close()
        return jsonres(0, 'ok', '删除成功')
    except fanhao.DoesNotExist:
        pass


def initsys():
    if not os.path.exists(PHOTO_PATH):
        os.mkdir(PHOTO_PATH)
    if not fanhao.table_exists():
        fanhao.create_table()
    db.close()
    print(os.path.exists('conf.d/config.ini'))


if __name__ == '__main__':

    initsys()
    app = web.Application()
    app.add_routes([
        web.route("*",'/', index),
        web.route("*",'/search', search),
        web.route("*",'/recode', recode),
        web.route("*",'/deimg', deimg),
        web.route("GET",'/set/{type}/{id}/{val}', set),
        web.static('/static', STATIC_PATH),
        web.static('/photos', PHOTO_PATH)
        ])
    web.run_app(app,port=getconfig('web','port'))
