# ArubaOS XML API client
This is a simple client for the [Aruba OS](http://www.arubanetworks.com/en-gb/products/networking/arubaos/)
[XML API](http://www.arubanetworks.com/techdocs/ArubaOS_60/UserGuide/XML_API.php).

Notably this allows programmatically changing the user name of clients in a "captive portal" role.

## Installation
```
pip install ArubaOS-XML-API
```

## Worked example

Here we configure ```my_service```, a wireless service using a custom captive portal. Our captive portal server is a web
server which knows how to authenticate our local, 1st party usernames.

We configure two Aruba users, each with a different role to manage what it can talk to on the network via ACLs:

 * One called ```my_service-login``` with role ```my_service-login_role```. This has just the ability to connect to the
   network (with DHCP and DNS) and talk to the captive portal server.
 * Another called ```my_service-open``` with role ```my_service-open_role```. This grants the user full access to
   network resources.

We configure RADIUS servers in ```my_service-srvgrp``` (not otherwise described) to support the default AAA profile 
using MAC authentication. The MAC authentication is configured to always succeed, and is used to record the start and
end of sessions as well as RADIUS accounting information. We do not change the user account of users once they have
completed MAC authentication, they should still be in "my_service-login_role" at this point. These RADIUS servers log
information about sessions to a database server which is also accessible to the captive portal server.

Next, the XML API is used to change the user ID of the connected client on login, from ```my_service-login``` to
```my_service-open```. It is the responsibility of the captive portal server to track which login events and (1st party)
usernames correspond to which sessions. The Aruba controller provides a lot of information to the captive portal server
in the redirection URL when redirecting users to facilitate this. The following named parameters are available:


| Parameter | Contents                                                   | Notes                                    |
|-----------|------------------------------------------------------------|------------------------------------------|
| cmd       | The action requested by the controller (?)                 | Seems to always be "login"               |
| switchip  | The IP address of the Aruba controller serving the client. | Must be enabled in captive-portal config |
| mac       | Client device MAC address                                  |                                          |
| ip        | Client device IP address                                   |                                          |
| essid     | ESSID to which the client is connected                     |                                          |
| apname    | Name of AP to which the client is connected                |                                          |
| apgroup   | Name of the group that contains the aforementioned AP      |                                          |
| url       | Original URL requested by the client before redirection    |                                          |


The captive portal server updates the database to add usernames to sessions being tracked by the RADIUS servers.

### Aruba configuration

**Configure Captive Portal server.** Assume ```https://login.wireless.example.com/``` is a web server running Python,
which can authenticate our (1st party) users somehow, and make use of the ArubaOS-XML-API Python module.
```
(host) (config) #aaa authentication captive-portal my_service-cp
(host) (Captive Portal Authentication Profile "my_service-cp") #login-page "https://login.wireless.example.com/"
(host) (Captive Portal Authentication Profile "my_service-cp") #switchip-in-redirection-url
```
Optionally, **configure bandwidth limits** for unauthenticated users:
```
(host) (config) #aaa bandwidth-contract unauth-down_bw kbits 768
(host) (config) #aaa bandwidth-contract unauth-up_bw kbits 256
```
**Define ACLs** for services that need to be accessible to unauthenticated users to allow them access to network services and our captive portal server. Also create an ACL that allows full network access.

(omitted for brevity, results in my_icmp-acl, my_dhcp-acl, my_dns-acl, my_service-captiveportal-acl and my_service-open-acl).
 
**Create users and roles.** Create a "login" user and role for users who are not yet logged in, with limited access to resources, and another "open" user and role for logged-in users with full access to network resources:
```
(host) (config) #local-userdb add username my_service-login password ... role my_service-login_role

(host) (config) #user-role my_service-login_role
(host) (config-role) #bw-contract unauth-up_bw per-user upstream
(host) (config-role) #bw-contract unauth-down_bw per-user downstream
(host) (config-role) #captive-portal "my_service-cp"
(host) (config-role) #access-list session my_icmp-acl
(host) (config-role) #access-list session my_dhcp-acl
(host) (config-role) #access-list session my_dns-acl
(host) (config-role) #access-list session my_service-captiveportal-acl

(host) (config) #local-userdb add username my_service-open password T0pS3cr3T role my_service-open_role

(host) (config) #user-role my_service-open_role
(host) (config-role) #access-list session my_icmp-acl
(host) (config-role) #access-list session my_dhcp-acl
(host) (config-role) #access-list session my_dns-acl
(host) (config-role) #access-list session my_service-open-acl
```
**Create an SSID** for the captive portal service:
```
(host) (config) #wlan ssid-profile my_service-ssid
(host) (SSID Profile "my_service-ssid") # essid "MyService"
```
**Create an XML API server:**
```
(master-a) (config) #aaa xml-api server 10.11.12.13
(master-a) (XML API Server "10.11.12.13") #key ArubaIsC00l
```

**Create an AAA profile** referencing the XML API server, and set a key for the XML API server
```
(host) (config) #aaa profile my_service-aaa
(host) (AAA Profile "my_service-aaa") #initial-role "my_service-login_role"
(host) (AAA Profile "my_service-aaa") #mac-default-role "my_service-login_role"
(host) (AAA Profile "my_service-aaa") #mac-server-group "my_service-srvgrp"
(host) (AAA Profile "my_service-aaa") #radius-accounting "my_service-srvgrp"
(host) (AAA Profile "my_service-aaa") #radius-interim-accounting
(host) (AAA Profile "my_service-aaa") #enforce-dhcp
(host) (AAA Profile "my_service-aaa") #xml-api-server 10.11.12.13
```
**Create a virtual AP** for the new SSID using this AAA profile
```
(host) (config) #wlan virtual-ap "my_service-vap"
(host) (Virtual AP profile "my_service-vap") #aaa-profile "my_service-aaa"
(host) (Virtual AP profile "my_service-vap") #ssid-profile "my_service-ssid"
(host) (Virtual AP profile "my_service-vap") #vlan ...
(host) (Virtual AP profile "my_service-vap") #broadcast-filter all
```

### Python code on captive portal server
Now we can finally write Python to record logins and update the user via the XML API:

The "authenticate" function is passed the 1st party username of the identified user, and the URL provided by the Aruba
controller which redirected the user. 
```python
from ArubaOS_XML_API import aruba_cmd
from my_database_functions import database_update_session # You get to write this yourself.
import requests

target_user = "my_service-open"
target_user_pass = "T0pS3cr3T"
aruba_key = "ArubaIsC00l"
aruba_key_type = "cleartext"

def authenticate(our_username, aruba_url):
    query = requests.utils.urlparse(aruba_url).query
    params = dict(x.split('=') for x in query.split('&'))
    database_update_session(our_username, params['mac'], params['ip'])
    aruba_result = aruba_cmd("user_authenticate", params['ip'], params['switchip'],
                             target_user, target_user_pass, aruba_key, aruba_key_type)
    # if aruba_result['status'] == "Ok":
    #     success = True
```
