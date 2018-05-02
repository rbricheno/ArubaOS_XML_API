import requests
import xml.etree.ElementTree as ElementTree


def aruba_cmd(cmd, ip_addr, controller_ip, user_id, password, aruba_key_hashed, aruba_key_type):
    """Python function to make requests of the ArubaOS XML API
       http://www.arubanetworks.com/techdocs/ArubaOS_60/UserGuide/XML_API.php"""
    aruba_url = "https://" + controller_ip + "/auth/command.xml"

    xml_out = """xml=<aruba command=\"""" + cmd + """\">
\t<ipaddr>""" + ip_addr + """</ipaddr>
\t<name>""" + user_id + """</name>
\t<password>""" + password + """</password>
\t<version>1.0</version>
\t<key>""" + aruba_key_hashed + """</key>
\t<authentication>""" + aruba_key_type + """</authentication>
</aruba>"""

    # Assume the controller is set up with an invalid SSL certificate. Don't use this on a public network.
    r = requests.post(aruba_url, data=xml_out, headers={'Content-Type': 'text/xml'}, verify=False)

    # This works (even in py<=2.6!) for the XML we get back from the ArubaOS controller when we send a single command.
    return dict((child.tag, child.text) for child in ElementTree.fromstring(r.text))
