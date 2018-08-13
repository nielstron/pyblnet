'''
Created on 12.08.2018

@author: Niels
'''

from pyblnet import BLNETWeb, test_blnet, BLNETDirect
from time import sleep

if __name__ == '__main__':

    ip = '192.168.178.10'
    
    print(test_blnet(ip))
    blnet = BLNETWeb(ip, timeout=5)
    #print(blnet.read_analog_values())
    #print(blnet.read_digital_values())
    
    #print(blnet.set_digital_value("10", 'AUS'))
    #print(blnet.read_digital_values())
    
    blnet = BLNETDirect(ip)
    #print(blnet.get_latest())
    #sleep(2)
    blnet._start_read()
    blnet._end_read(True)
    print(blnet.get_data(1))
