"""
Test some of the ezproxy infrastructure stuff.
"""

import mock

from basetestcase import BaseTestCase

from paperbot.ezproxy import (
    load_ezproxy_config,
)


class EzproxyTestCases(BaseTestCase):
    def test_load_ezproxy_config_path_does_not_exist(self):
        with mock.patch("os.path.exists", return_value=False) as ospathexists:
            load_ezproxy_config()
            self.assertTrue(ospathexists.called)

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("os.listdir", return_value=["test.json"])
    @mock.patch("paperbot.ezproxy.load_json_file", return_value={})
    def test_load_ezproxy_config_calls_file_reader(self, load_json_file,
                                                   oslistdir, ospathexists):
        load_ezproxy_config()
        self.assertTrue(load_json_file.called)

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("paperbot.ezproxy.load_json_file", return_value={})
    def test_load_ezproxy_config_bails_on_no_json_filename(self,
                                                           load_json_file,
                                                           ospathexists):
        with mock.patch("os.listdir", return_value=["something.xml"]):
            output = load_ezproxy_config()

        # should still have returned a dictionary
        self.assertTrue(isinstance(output, dict))

        # should not have attempted to load xml file
        self.assertFalse(load_json_file.called)

    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("os.listdir", return_value=["test.json"])
    def test_load_ezproxy_config_loads_dict(self, oslistdir, ospathexists):
        testjson = {
            "url": "http://httpbin.org/",
            "data": {
                "User": "jj",
                "pw": "91",
            },
        }

        with mock.patch("paperbot.ezproxy.load_json_file",
                        return_value=testjson):
            output = load_ezproxy_config()

        # should still be a dictionary result
        self.assertTrue(isinstance(output, dict))

        # but the dict should not be empty
        self.assertNotEqual(output, {})

        # this is based on listdir returning "test.json"
        self.assertTrue("test" in output.keys())

        # loaded config should be same as test config
        self.assertEqual(output["test"], testjson)
