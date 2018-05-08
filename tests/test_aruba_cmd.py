import mock
import unittest
import ArubaOS_XML_API


class FakeElement(object):
    def __init__(self, tag, text):
        self.tag = tag
        self.text = text


class TestArubaCmd(unittest.TestCase):
    """Tests for `aruba_cmd.py`."""

    @mock.patch('requests.post')
    @mock.patch('xml.etree.ElementTree.fromstring')
    def test_aruba_cmd(self, mock_element_tree_fromstring, mock_post):
        cmd = "user_authenticate"
        ip_addr = "192.168.1.7"
        switchip = "192.168.1.3"
        user_id = "open_role"
        target_user_pass = "secret"
        aruba_key = "abc123"
        aruba_key_type = "cleartext"

        desired_xml = """xml=<aruba command=\"""" + cmd + """\">
\t<ipaddr>""" + ip_addr + """</ipaddr>
\t<name>""" + user_id + """</name>
\t<password>""" + target_user_pass + """</password>
\t<version>1.0</version>
\t<key>""" + aruba_key + """</key>
\t<authentication>""" + aruba_key_type + """</authentication>
</aruba>"""
        desired_url = "https://" + switchip + "/auth/command.xml"

        fake_response = """<aruba>
\t<status>Ok</status>
\t<code>0</code>
</aruba>"""

        fake_element_tree = [FakeElement("status", "Ok"), FakeElement("code", 0)]

        mock_post.return_value.text = fake_response
        mock_element_tree_fromstring.return_value = fake_element_tree

        self.assertEqual(ArubaOS_XML_API.aruba_cmd("user_authenticate", ip_addr, switchip, user_id,
                                                   target_user_pass, aruba_key, aruba_key_type),
                         {'code': 0, 'status': 'Ok'})
        mock_post.assert_called_with(desired_url, data=desired_xml,
                                     headers={'Content-Type': 'text/xml'}, verify=False)
        mock_element_tree_fromstring.assert_called_with(fake_response)
