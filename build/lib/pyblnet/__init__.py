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

class BLNET(object):
    '''
    Interface to communicate with the UVR1611 over his web surface (BL-Net)
    Attributes:
        ip         The ip of the UVR1611/BL-Net to connect to
        password   the password to log into the web interface provided
    '''
    ip = ""
    _def_password = "0128" #default password is 0128
    password = ""
    current_taid = "" # TAID cookie in the form 'TAID="EEEE"'

    def __init__(self, ip, password = _def_password):
        '''
        Constructor
        '''
       
        if "http://" not in ip :
            ip = "http://" + ip
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
    
    def read_analog_values(self):
        '''
        Reads all analog values (temperatures, speeds) from the web interface
        and returns list of quadruples of id, name, value, unit of measurement
        '''
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
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(?P<value>\d+,\d+) " +
            "(?P<unit_of_measurement>.+?) &nbsp;&nbsp;PAR?", 
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
    
    def read_digital_values(self):
        '''
        Reads all digital values (switches) from the web interface
        and returns list of quadruples of id, name, mode (AUTO/HAND), value 
        (EIN/AUS)
        '''
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
        '''
        
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
        
        # return whether we were still logged in
        return r.headers.get('Set-Cookie') != None
        