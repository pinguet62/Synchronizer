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

print (__file__)

class TestActions(unittest.TestCase):
    _TEST_FOLDER = "tests"
    _TEST_FOLDER_SRC = os.path.join(_TEST_FOLDER, "Cas_test_sauv")
    _TEST_FOLDER_TGT = os.path.join(_TEST_FOLDER, "Cas_test")
    _SRC = os.path.join(_TEST_FOLDER_TGT, "src")
    _TGT = os.path.join(_TEST_FOLDER_TGT, "tgt")
    
    def setUp(self):
        if os.path.exists(TestActions._TEST_FOLDER_TGT):
            shutil.rmtree(TestActions._TEST_FOLDER_TGT)
        shutil.copytree(TestActions._TEST_FOLDER_SRC, TestActions._TEST_FOLDER_TGT)
    
    def _pathToRelpath(self, relpath):
        return os.path.join(TestActions._SRC, relpath)
    
    def _actionForRelpath(self, actions, cls, relpath):
        '''
        Get the number of action in the list, who corresponding to the relative path.
        @param actions: The actions.
        @param cls: The action class.
        @param relpah: The relative path from the source or target folder.
        @return: The number of actions who match.
        '''
        return len([action for action in actions if isinstance(action, cls) and os.stat(self._pathToRelpath(action.relpath)) == os.stat(self._pathToRelpath(relpath))])
    
    def test_Analyzer(self):
        actions = []
        
        def validate():
            self.assertEqual(14, len(actions))
            self.assertEqual(1, self._actionForRelpath(actions, GUI.CopyAction, 'add src folder'))
        
        analyzer = GUI.Analyzer(TestActions._SRC, TestActions._TGT)
        analyzer.handler = lambda action: actions.append(action)
        analyzer.after = validate
        analyzer.start()


if __name__ == '__main__':
    unittest.main()