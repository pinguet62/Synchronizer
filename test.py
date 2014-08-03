#!/usr/bin/python
# -*- coding: utf-8 -*-


'''Test for the Synchronizer application.'''


import os
import shutil
import unittest

import GUI


__author__ = __maintainer__ = 'Pinguet62'
__date__ = '2014/06/02'
__email__ = 'pinguet62@gmail.com'
__license__ = 'Creative Commons, Attribution NonCommercial ShareAlike, 4.0'
__status__ = 'Develpment'
__version__ = '2.0' 


class TestActions(unittest.TestCase):
    _TEST_FOLDER = "tests"
    _TEST_FOLDER_SRC = os.path.join(_TEST_FOLDER, "Cas_test_sauv")
    _TEST_FOLDER_TGT = os.path.join(_TEST_FOLDER, "Cas_test")
    
    _SRC = os.path.joint(_TEST_FOLDER_TGT, "src")
    _TGT = os.path.joint(_TEST_FOLDER_TGT, "src")
    
    def setUp(self):
        if os.path.exists(TestActions._TEST_FOLDER_TGT):
            shutil.rmtree(TestActions._TEST_FOLDER_TGT)
        shutil.copytree(TestActions._TEST_FOLDER_SRC, TestActions._TEST_FOLDER_TGT)
    
    def test_Analyzer(self):
        actions = []
        
        def validate():
            pass
        
        analyzer = GUI.Analyzer(_SRC, _TGT)
        analyzer.handler = lambda action: actions.append(action)
        analyzer.after = validate
        analyzer.start()


if __name__ == '__main__':
    unittest.main()