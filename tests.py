import unittest
import pycodestyle
import os
import re
import json

from app import app

'''
__author__ = "Phil Nicholls"
__copyright__ = "Copyright 2020, Phil Nicholls"
__credits__ = ["Phil Nicholls"]
__license__ = "GNUv3"
__version__ = "0.1.0"
__maintainer__ = "Phil Nicholls"
__email__ = "phil.j.nicholls@gmail.com"
__status__ = "Development"
__tests__ = ["pep8", "todo"]
'''


def get_tests(filename):
    '''
    Gets a tests array from the docstring meta tag
    for a source file
    '''

    tests = []

    file = open(filename, 'r')

    for line in file:
        if line.startswith('__tests__'):
            tests_string = re.findall(r'\[(.*)\]', line)
            tests = re.findall('["\']?([^"\']+)["\']?', tests_string[0])
            break

    file.close()

    return tests


class TestTodo(unittest.TestCase):
    def test_check_source_for_todo(self):
        files_to_test = []

        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                if file.endswith(".py"):
                    if 'todo' in get_tests(os.path.join(root, file)):
                        files_to_test.append(os.path.join(root, file))

        for file_name in files_to_test:
            file = open(file_name, 'r')

            for line_num, line in enumerate(file, start=1):
                with self.subTest():
                    '''
                    upper() is used to avoid triggering the
                    todo check on this file
                    '''
                    self.assertNotIn(
                        'todo'.upper(),
                        line,
                        'todo'.upper() + 'found on line ' +
                        str(line_num) +
                        ' of ' +
                        file_name)
            file.close()


class PEP8TestCase(unittest.TestCase):
    def test_check_source_for_pep8(self):
        files_to_test = []

        for root, dirs, files in os.walk(os.getcwd()):
            for file in files:
                if file.endswith(".py"):
                    if 'pep8' in get_tests(os.path.join(root, file)):
                        files_to_test.append(os.path.join(root, file))

        for file in files_to_test:
            fchecker = pycodestyle.Checker(file, show_source=True)
            file_errors = fchecker.check_all()
            with self.subTest():
                self.assertTrue(
                    file_errors == 0,
                    'Found %s pep8 errors.' %
                    file_errors)

class SendToKindleTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_send_webpages(self):
        payload = {
            'url': 'https://realpython.com/python-testing/',
        }

        response = self.app.post('/', data=payload)

        self.assertIsNotNone(response.json)
        self.assertEqual(bool, type(response.json['success']))
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json['success'])

    def test_missing_url(self):
        payload = {}

        response = self.app.post('/', data=payload)

        self.assertEqual(400, response.status_code)

    def test_bad_url(self):
        payload = {
            'url': 'http://dgdgjs.fff/dhdgdyu'
        }

        response = self.app.post('/', data=payload)

        self.assertEqual(404, response.status_code)

if __name__ == '__main__':
    unittest.main()
