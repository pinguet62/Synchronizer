#!/usr/bin/python
# -*- coding: utf-8 -*-



'''The action to execute on files.'''



__author__ = __maintainer__ = 'Pinguet62'
__date__ = '2014/08/01'
__email__ = 'pinguet62@gmail.com'
__license__ = 'Creative Commons, Attribution NonCommercial ShareAlike, 4.0'
__status__ = 'Develpment'
__version__ = '2.0'



import logging
import os
import threading



logging.config.fileConfig('logging.conf')
logger = logging.getLogger('synchronyzer')  # TODO: 'action'



def delete(path):
    '''
    Delete the file or folder.
    @param path: Path to object.
    '''
    
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)



class Action:
    '''The abstract class of actions.'''
    
    
    def __init__(self, relpath, srcPath, tgtPath):
        self.relpath = relpath
        '''The relative path to object.'''
        self.srcPath = srcPath
        '''The source folder.'''
        self.tgtPath = tgtPath
        '''The target folder.'''
    
    
    def execute(self):
        raise NotImplementedError
    
    
    def getExtension(self):
        return os.path.splitext(self.relpath)[1]
    
    
    def getName(self):
        '''Abstract method who get the name of the action.'''
        raise NotImplementedError
    
    
    def _getSize(self, path):
        '''
        Get the size of object.
        @param path: The path to object.
        @return: The size.
        '''
        if os.path.isdir(path):
            size = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    size += os.path.getsize(os.path.join(root, file))
            return size
        else:
            return os.path.getsize(path)
    
    
    def getSize(self):
        '''
        Get the size of the object.
        @return: The size.
        '''
        return self._getSize(self.srcPath)



class CopyAction(Action):
    '''Add the new file.'''
    
    def __init__(self, relpath, srcPath, tgtPath):
        Action.__init__(self, relpath, srcPath, tgtPath)
    
    
    def getName(self):
        return 'Add'
    
    
    def execute(self):
        if os.path.isdir(self.srcPath):
            shutil.copytree(self.srcPath, self.tgtPath)
        else:
            shutil.copy2(self.srcPath, self.tgtPath)



class UpdateAction(Action):
    '''Replace the old object by the latest.'''
    
    
    def __init__(self, relpath, srcPath, tgtPath):
        Action.__init__(self, relpath, srcPath, tgtPath)
    
    
    def getName(self):
        return 'Update'
    
    
    def execute(self):
        delete(self.tgtPath)
        if os.path.isdir(self.srcPath):
            shutil.copytree(self.srcPath, self.tgtPath)
        else:
            shutil.copy2(self.srcPath, self.tgtPath)



class RemoveAction(Action):
    '''Remove the old saved file.'''
    
    
    def __init__(self, relpath, srcPath, tgtPath):
        Action.__init__(self, relpath, srcPath, tgtPath)
    
    
    def getName(self):
        return 'Remove'
    
    
    def execute(self):
        delete(self.tgtPath)
    
    
    def getSize(self):
        '''
        Get the size of tgt object.
        @return: The size.
        '''
        return self._getSize(self.tgtPath)



class Analyzer(threading.Thread):
    '''Thread to compare two folders and generate the actions.'''
    
    
    def __init__(self, src, tgt):
        threading.Thread.__init__(self, target=self.run, name='Folder analyze')
        
        self.src = src
        self.tgt = tgt
        self._stop = False
        self.handler = None
        self.after = None
    
    
    def run(self):
        '''
        Run the analyze.
        @param actionHandler: Function called when an action is find. It take the action in parameter.
        '''
        logger.info("Analyze running...")
        logger.info("Source: " + self.src)
        logger.info("Target: " + self.tgt)
        self._execute('.')
        if self.after is not None: self.after()
        logger.info("Analyze terminated.")
    
    
    def stop(self):
        '''Stop the analyze, and terminate the thread.'''
        self._stop = True
    
    
    def _callHandler(self, action):
        '''
        Call the handler.
        @param action: The action.
        '''
        if self.handler is not None: self.handler(action)
    
    
    
    def _execute(self, subfolder):
        '''
        Method who browse directories recursively.
        @param subfolder: The relative path to sub-folder.
        '''
        srcFolder = os.path.join(self.src, subfolder)
        tgtFolder = os.path.join(self.tgt, subfolder)
        for obj in set(os.listdir(srcFolder) + os.listdir(tgtFolder)):
            if self._stop:
                return
            
            relpath = os.path.join(subfolder, obj)
            srcPath = os.path.join(self.src, relpath)
            tgtPath = os.path.join(self.tgt, relpath)
            
            if not os.path.exists(srcPath):
                if os.path.exists(tgtPath):
                    self._callHandler(RemoveAction(relpath, srcPath, tgtPath))
                else: pass  # ???
            elif os.path.isfile(srcPath):
                if not os.path.exists(tgtPath):
                    self._callHandler(CopyAction(relpath, srcPath, tgtPath))
                elif os.path.isfile(tgtPath):
                    if os.path.getmtime(tgtPath) > os.path.getmtime(srcPath) + 0.0001:
                        self._callHandler(UpdateAction(relpath, srcPath, tgtPath))
                elif os.path.isdir(tgtPath):
                    self._callHandler(UpdateAction(relpath, srcPath, tgtPath))
                else: pass
            elif os.path.isdir(srcPath):
                if not os.path.exists(tgtPath):
                    self._callHandler(CopyAction(relpath, srcPath, tgtPath))
                elif os.path.isfile(tgtPath):
                    self._callHandler(UpdateAction(relpath, srcPath, tgtPath))
                elif os.path.isdir(tgtPath):
                    self._execute(relpath)
                else: pass
            else: pass
