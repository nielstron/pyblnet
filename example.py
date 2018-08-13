'''
Created on 12.08.2018

@author: Niels
'''

from pyblnet import BLNETWeb, test_blnet, BLNETDirect

if __name__ == '__main__':

    ip = '192.168.178.10'
    
    # Check if there is a blnet at given address
    print(test_blnet(ip))
    # Fetch the latest data via web interface
    blnet = BLNETWeb(ip, timeout=5)
    print(blnet.read_analog_values())
    print(blnet.read_digital_values())
    
    # For publishing values
    #print(blnet.set_digital_value("10", 'AUS'))
    #print(blnet.read_digital_values())
    
    blnet = BLNETDirect(ip)
    # Fetching the latest data from the backend
    print(blnet.get_latest())
    # Still inofficial because unexplicably failing often
    print(blnet._get_data(1))
