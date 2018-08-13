'''
Created on 13.08.2018

@author: Niels
'''
from pyblnet.blnet_web import BLNETWeb 
from pyblnet.blnet_conn import BLNETDirect

class BLNET(object):
    '''
    General high-level BLNET class, using just
    what is available and more precise
    '''


    def __init__(self, address, web_port=80, password=None, ta_port=40000,
                 timeout=5, max_retries=5):
        '''
        If a connection (Web or TA/Direct) should not be used,
        set the corresponding port to None
        Params:
        @param ta_port: Port for direct TCP Connection
        '''
        assert(isinstance(address, str))
        assert(web_port is None or isinstance(web_port, int))
        assert(ta_port is None or isinstance(ta_port, int))
        assert(timeout is None or isinstance(timeout, int))
        self.address = address
        self.timeout = timeout
        self.max_retries = max_retries
        if web_port is not None:
            self.blnet_web = BLNETWeb(address, password, timeout)
        if ta_port is not None:
            self.blnet_direct = BLNETDirect(address, ta_port)
    
    def fetch(self, node=None):
        '''
        Fetch all available data about selected node
        '''
        data = {
            'analog': {},
            'digital': {},
            'speed': {},
            'energy': {},
            'power': {},
        }
        if self.blnet_web:
            if node is not None:
                self.blnet_web.set_node(node)
            data['analog'] = self._convert_web(
                self.blnet_web.read_analog_values()
            )
            data['digital'] = self._convert_web(
                self.blnet_web.read_digital_values()
            )
        if self.blnet_direct:
            direct = self.blnet_direct.get_latest(self.max_retries)[0]
            # Override values for analog and digital as values are
            # expected to be more precise here
            for domain in ['analog', 'digital']:
                for id, value in direct[domain].items():
                    if data[domain].get(id) is not None:
                        data[domain][id]['value'] = value
            for domain in ['speed', 'energy', 'power']:
                for id, value in direct[domain].items():
                    if value is None:
                        continue
                    data[domain][id] = {
                        'value': value
                    }
        return data
        
    def _convert_web(self, values):
        '''
        Converts data returned by blnet_web to nice data
        '''
        data = {}
        for sensor in values:
            data[int(sensor['id'])] = sensor
        return data
        
        