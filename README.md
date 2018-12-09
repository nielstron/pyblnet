# PyBLNET - a very basic python BL-NET bridge
A package that connects to the BL-NET that is connected itself to a UVR1611 device by Technische Alternative. 
It is able to read digital and analog values as well as to set switches to ON/OFF/AUTO.

Documentation on the modules and their methods can be found with the methods and modules themselves.

### Usage

```python
ip = '192.168.178.10'

# Check if there is a blnet at given address
test_blnet(ip) # -> True/False

# Convenient high level interface
blnet = BLNET(ip, timeout=5)

# Control a switch by its ID
blnet.turn_on(10)
blnet.turn_auto(10)
blnet.turn_off(10)

# Fetch data (contains all available data using enabled interfaces)
print(blnet.fetch())



# The low level modules are also available
# note that the direct use of these modules is discouraged though

# Fetch the latest data via web interface
blnet = BLNETWeb(ip, timeout=5)
print(blnet.read_analog_values())
print(blnet.read_digital_values())

# For publishing values
blnet.set_digital_value('10', 'AUS')

# Fetch data via the Protocol developed by TA
blnet = BLNETDirect(ip)
# Fetching the latest data
print(blnet.get_latest())
# Still inofficial because unexplicably failing often
print(blnet._get_data(1))
```
