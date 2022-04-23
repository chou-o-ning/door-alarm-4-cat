#    Copyright [2022] [chou.o.ning@gmail.com]

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import socket
import struct
import json
import time
import logging

from wxpusher import WxPusher

_LOGGER = logging.getLogger(__name__)

# wxpusher 参数

UID = 'UID_xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TOPIC_IDs = 'yyyy'
TOKEN = "AT_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

TIME_OF_OPEN = 30  # 门开启的时间，超过则推送告警信息

Log_Format = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(filename = "logfile.log",
                    filemode = "w",
                    format = Log_Format, 
                    level = logging.WARNING)

multi_cast_group = '224.0.0.50' # 播组
server_address = ('', 9898) # 播组端口

# Create the socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(False) 
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind to the server address
sock.bind(server_address)

# Tell the operating system to add the socket to the multi_cast group on all interfaces.
group = socket.inet_aton(multi_cast_group)
m_req = struct.pack('4sL', group, socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, m_req)

pusher  = WxPusher
pusher.default_token = TOKEN

open_time = 0
message_send = 0
message_send_noon = 0
# Receive/respond loop
while True:
    try:
        data, address = sock.recvfrom(65535) # socket的recvfrom()会返回数据以及相应的地址
        jstr = data.decode('utf-8')
        sdata = json.loads(jstr)
        if (sdata['cmd'] == 'report') and (sdata['model'] == 'sensor_magnet.aq2') and (sdata['sid'] == '158d000445872e'):
                for param in sdata['params']:
                        # 门打开
                        if param['window_status'] == 'open':
                                open_time = int(time.time())
                                _LOGGER.warning("door open at: " + str(open_time))
                        # 门关闭
                        if param['window_status'] == 'close':
                                _LOGGER.warning("door close at: " + str(int(time.time())))
                                if message_send == 1:
                                        res = pusher.send_message('告警消除：门已关闭', 
                                                uids=[UID,], topic_ids = [TOPIC_IDs,])
                                        _LOGGER.warning(res)
                                        _LOGGER.warning('告警消除：门已关闭')
                                open_time = 0
                                message_send = 0

        # 门开了，还没有关，超出了 TIME_OF_OPEN
        if (message_send == 0) and (open_time > 0) and (int(time.time()) - open_time > TIME_OF_OPEN):
                res = pusher.send_message('告警：门开启超过' + str(TIME_OF_OPEN) + '秒', 
                        uids=[UID,], topic_ids = [TOPIC_IDs,])
                _LOGGER.warning(res)
                _LOGGER.warning('告警：门开启超过' + str(TIME_OF_OPEN) + '秒')
                message_send = 1

        # 每日中午午饭提醒，表明程序还在正常运行
        localtime = time.localtime(time.time())
        if (message_send_noon == 0) and (localtime.tm_hour == 12) and (localtime.tm_min == 0) and (localtime.tm_sec == 0):
                res = pusher.send_message('午饭提醒', 
                uids=[UID,], topic_ids = [TOPIC_IDs,])
                _LOGGER.warning(res)
                message_send_noon = 1
        if (localtime.tm_hour == 12) and (localtime.tm_min == 1) and (localtime.tm_sec == 0):
                message_send_noon = 0

    except BlockingIOError: 
        time.sleep(0.1)
