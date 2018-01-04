'''
Created on 26.09.2017

@author: Nielstron
'''

import requests
from htmldom import htmldom
import html.parser
import re 
from sre_compile import isstring
from builtins import int
from test.test_binop import isint
import socket
import ipaddress

"""
def detect_blnet(subnet = socket.gethostbyname(socket.getfqdn())):
    '''
    Detects a blnet in the local network and returns its ip
    NOT WORKING IN MY NETWORK
    Attributes:
        subnet    the subnet to search for the blnet
    Returns:
        ip address of BLNET or None if none found
    '''
    # iterate through local network in search for blnet
    net4 = ipaddress.ip_network(subnet)
    print(list(net4.hosts()))
    for pos_ip in net4.hosts():
        print('Testing '+ str(pos_ip))
        if test_blnet(str(pos_ip)):
            return pos_ip
    return None
"""
            
def test_blnet(ip):
    '''
    Tests whether an BLNET answers under given ip
    Attributes:
        ip      IP of the BLNET
    '''
    if "http://" not in ip and "https://" not in ip:
        ip = "http://" + ip
    r = requests.get(ip)
    # Parse  DOM object from HTMLCode
    dom = htmldom.HtmlDom().createDom(r.text)
    # either a 'Zugriff verweigert' message is shown
    if 'BL-Net Zugang verweigert' in dom.find('title').text():
        return True
    # or (more often) the BL-NET Menü
    if 'BL-NET' in dom.find('div#head').text():
        return True
    return False

class BLNET(object):
    '''
    Interface to communicate with the UVR1611 over his web surface (BL-Net)
    Attributes:
        ip         The ip/domain of the UVR1611/BL-Net to connect to
        password   the password to log into the web interface provided
    '''
    ip = ""
    _def_password = "0128" #default password is 0128
    password = ""
    current_taid = "" # TAID cookie in the form 'TAID="EEEE"'

    def __init__(self, ip = False, password = _def_password):
        '''
        Constructor
        '''
        # if ip is omitted, search for UVR yourself
        #if not ip: ip = detect_blnet() - not working yet
        if "http://" not in ip and "https://" not in ip:
            ip = "http://" + ip
        if not test_blnet(ip): 
            raise ValueError('No BLNET found under given address')
        self.ip = ip
        self.password = password
        
    
    def logged_in(self):
        '''
        Determines whether the object is still connected to the BLNET
        / Logged into the web interface
        '''
        # check if a request to a restricted page returns a cookie if
        # we have sent one (if our cookie is the current one this
        # would be the case)
        r = requests.get(
            # restricted page is chosen to be small in data
            # so that it can be quickly loaded
            self.ip + "/par.htm?blp=A1200101&1238653",
            headers = self.cookie_header()
            )
        return r.headers.get('Set-Cookie') != None
    
    def cookie_header(self):
        '''
        Creates the header to pass the session TAID as cookie
        '''
        headers = {'Cookie': self.current_taid }
        return headers
    
    def log_in(self):
        '''
        Logs into the BLNET interface, renews the TAID
        '''
        if self.logged_in(): return True
        payload = {
            'blu' : 1, # log in as experte
            'blp' : self.password,
            'bll' : "Login"
            }
        headers = {
            'Content-Type' : 'application/x-www-form-urlencoded'
            }
        r = requests.post(
            self.ip + '/main.html',
             data = payload, headers = headers)
        #try two times to log in
        i = 0
        while i < 2:
            self.current_taid = r.headers.get('Set-Cookie')
            i += 1
            if self.logged_in():
                return True
        return False
        
    
    def log_out(self):
        '''
        Logs out of the BLNET interface
        '''
        requests.get(
            self.ip + "/main.html?blL=1",
             headers = self.cookie_header())
        return not self.logged_in()
    
    def set_node(self, node):
        '''
        Selects the node at which the UVR of interest lies
        future requests will be sent at this particular UVR
        '''
        # ensure to be logged in
        if not self.log_in(): return None
        
        # send the request to change the node
        r = requests.get(
            self.ip + "/can.htm?blaA=" + str(node),
            headers = self.cookie_header())
        # return whether we we're still logged in => setting went well
        return r.headers.get('Set-Cookie') != None
    
    def read_analog_values(self):
        '''
        Reads all analog values (temperatures, speeds) from the web interface
        and returns list of quadruples of id, name, value, unit of measurement
        '''
        # ensure to be logged in
        if not self.log_in(): return None
        # create a HTMLParser for later
        h = html.parser.HTMLParser()
        
        if not self.logged_in(): self.log_in()
        r = requests.get(
            self.ip + "/580500.htm",
            headers = self.cookie_header())
        # Parse  DOM object from HTMLCode
        dom = htmldom.HtmlDom().createDom(r.text)
        # get the element containing the interesting information
        dom = dom.find("div.c")[1]
        # filter out the text
        data_raw = dom.text()
        
        # collect data in an array
        data = list()
        
        # search for data by regular expression
        match_iter = re.finditer(
            "&nbsp;(?P<id>\d+):&nbsp;(?P<name>.+)\n" +
            "(&nbsp;){3,6}(?P<value>\d+,\d+) " +
            "(?P<unit_of_measurement>.+?) &nbsp;&nbsp;PAR?", 
            data_raw)
        match = next(match_iter, False)
        # parse a dict of the match and save them all in a list
        while match:
            match_dict = match.groupdict()
            # convert html entities to unicode characters
            for key in match_dict.keys():
                match_dict[key] = h.unescape(match_dict[key])
                # also replace decimal "," by "." 
                match_dict[key] = match_dict[key].replace(",", ".")
            # and append formatted dict
            data.append(match_dict)
            match = next(match_iter, False)
        return data
    
    def read_digital_values(self):
        '''
        Reads all digital values (switches) from the web interface
        and returns list of quadruples of id, name, mode (AUTO/HAND), value 
        (EIN/AUS)
        '''
        # ensure to be logged in
        if not self.log_in(): return None
        # create a HTMLParser for later
        h = html.parser.HTMLParser()
        
        if not self.logged_in(): self.log_in()
        r = requests.get(
            self.ip + "/580600.htm",
            headers = self.cookie_header())
        # Parse  DOM object from HTMLCode
        dom = htmldom.HtmlDom().createDom(r.text)
        # get the element containing the interesting information
        dom = dom.find("div.c")[1]
        
        # filter out the text
        data_raw = dom.text()

        # collect data in an array
        data = list()
        
        # search for data by regular expression
        match_iter = re.finditer(
            "&nbsp;(?P<id>\d+):&nbsp;(?P<name>.+)\n" +
            "&nbsp;&nbsp;&nbsp;&nbsp;(?P<mode>(AUTO|HAND))/" + 
            "(?P<value>(AUS|EIN))", 
            data_raw)
        match = next(match_iter, False)
        # parse a dict of the match and save them all in a list
        while match:
            match_dict = match.groupdict()
            # convert html entities to unicode characters
            for key in match_dict.keys():
                match_dict[key] = h.unescape(match_dict[key])
            # and append formatted dict
            data.append(match_dict)
            match = next(match_iter, False)
        return data
    
    def set_digital_value(self, id, value):
        '''
        Sets a digital value with given id to given value 
        Accepts 'EIN' and everything evaluating to True
        as well as 'AUS' and everything evaluating to False
        and 'AUTO' as values
        Attributes:
            id       id of the device whichs state should be changed
            value    value to change the state to
        '''
        # throw error for wrong id's
        if id < 1: raise ValueError('Device id can\'t be smaller than 1')
        # ensure to be logged in
        if not self.log_in(): return False
        
        # transform input value to 'EIN' or 'AUS'
        if value == 'AUTO':
            value = '3' # 3 means auto
        elif value != 'AUS' and value:
            value = '2' # 2 means turn on
        else:
            value = '1' # 1 means turn off
        
        # convert id to hexvalue so that 10 etc become A...
        hex_repr = [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'A', 'B', 'C', 'D','E', 'F']
        if isstring(id): id = int(id, 10)
        if id > 9:
            id = hex_repr[id]
        
        # transform id to string
        if not isstring(id): id = str(id)
        
        # submit data to website
        r = requests.get(
            self.ip + "/580600.htm?blw91A1200" + id + "=" + value ,
            headers = self.cookie_header())
        
        # return whether we we're still logged in => setting went well
        return r.headers.get('Set-Cookie') != None
        