#!/usr/bin/python
# -*- coding: utf-8 -*-



'''Synchronise two folders.'''



# TODO: wx.ID_ANY



__author__ = __maintainer__ = 'Pinguet62'
__date__ = '2014/06/02'
__email__ = 'pinguet62@gmail.com'
__license__ = 'Creative Commons, Attribution NonCommercial ShareAlike, 4.0'
__status__ = 'Develpment'
__version__ = '2.0'



import logging
import logging.config
import os
import shutil
import threading
import time

import win32com.shell.shell
import win32com.shell.shellcon
import win32con
import win32gui
import win32clipboard
import wx

import action



logging.config.fileConfig('logging.conf')
logger = logging.getLogger('synchronyzer')  # TODO: 'GUI'



def octet_to_human(size):
    '''
    Convert the number of octets to metric prefix value.
    @param size: The size, in octet.
    @return The human representation.
    '''
    
    # o
    if size < 1024 ** 1:
        return '%do' % size
    # ko
    elif size < 1024 ** 2:
        return '%.1fko' % (size / 1024)
    # Mo
    elif size < 1024 ** 3:
        return '%.1fMo' % (size / 1024 ** 2)
    # Go
    elif size < 1024 ** 4:
        return '%.1fGo' % (size / 1024 ** 3)
    # To
    else:
        return '%.1fTo' % (size / 1024 ** 4)



def get_extension(path):
    '''
    Get the extension of object.
    @param path: The path to object.
    @return The extension, "folder" if it's a folder.
    '''
    
    if os.path.isdir(path):
        return 'folder'
    elif os.path.isfile(path):
        return os.path.splitext(path)[1].lower()
    else:
        return ''



def bitmap_from_extension(extension):
    '''
    Get the bitmap of extension.
    @param extension: The extension.
    @return The image.
    '''
    
    if extension == 'folder':
        bm = wx.Bitmap(name='icons/folder.png', type=wx.BITMAP_TYPE_PNG)
        bm.SetSize((16, 16))
        return bm
    else:
        flags = win32com.shell.shellcon.SHGFI_SMALLICON | win32com.shell.shellcon.SHGFI_ICON | win32com.shell.shellcon.SHGFI_USEFILEATTRIBUTES
        retval, info = win32com.shell.shell.SHGetFileInfo(extension,
                                                          win32con.FILE_ATTRIBUTE_NORMAL,
                                                          flags)
        icon = wx.EmptyIcon()
        icon.SetHandle(info[0])
        return wx.BitmapFromIcon(icon)



class MyListCtrl(wx.ListCtrl):
    '''Override of wx.ListCtrl.'''
    
    # Columns
    _PATH = 0
    _EXTENSION = 1
    _ACTION = 2
    _TAILLE = 3
    
    def __init__(self, parent):
        '''
        Constructor.
        @param parent: The parent.
        '''
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT)
        
        self.actions = []
        
        # Column names
        self.InsertColumn(col=MyListCtrl._PATH, heading='Path', width=200)
        self.InsertColumn(col=MyListCtrl._EXTENSION, heading='Extension', width=65)
        self.InsertColumn(col=MyListCtrl._ACTION, heading='Action', width=89)
        self.InsertColumn(col=MyListCtrl._TAILLE, heading='Taille', width=60)
        
        # Icons
        self._imageList = wx.ImageList(width=16, height=16)
        self.extension_imageIndex = {}  # Dictionnaire: extension du fichier -> indice de l'image
        
        # Events
        self.Bind(event=wx.EVT_LIST_ITEM_RIGHT_CLICK, handler=self.OnItemRightClick)
        self.Bind(event=wx.EVT_LIST_KEY_DOWN, handler=self.OnKeyDown)
    
    
    def _getImageIndex(self, extension=''):
        '''
        Obtenir l'indice de l'image à partir de son extension.
        @param extension: The extension.
        @return The index.
        '''
        if extension in self.extension_imageIndex:
            return self.extension_imageIndex[extension]
        else:
            bmp = bitmap_from_extension(extension)
            # Save image
            indice = self._imageList.Add(bmp)
            self.SetImageList(self._imageList, wx.IMAGE_LIST_SMALL)
            # Save index
            self.extension_imageIndex[extension] = indice
            return indice
    
    
    def Add(self, action):
        '''
        Add new action to list.
        @param action: The action.
        '''
        self.actions.append(action)
        
        num = self.GetItemCount()
        extension = action.getExtension()
        self.InsertStringItem(index=num, label=action.relpath, imageIndex=self._getImageIndex(extension))
        self.SetStringItem(index=num, col=MyListCtrl._EXTENSION, label='' if extension == 'folder' else extension)
        self.SetStringItem(index=num, col=MyListCtrl._ACTION, label=action.getName())
        self.SetStringItem(index=num, col=MyListCtrl._TAILLE, label=octet_to_human(action.getSize()))
    
    
    def DeleteLine(self, index):
        '''
        Delete a line.
        @param index: The line index.
        '''
        del self.actions[index]
        self.DeleteItem(item=index)
    
    
    def DeleteSelectedLines(self):
        '''Delete the selected lines.'''
        index = self.GetFirstSelected()
        while index != -1:
            self.DeleteLine(index)
            index = self.GetFirstSelected()
    
    
    def OnKeyDown(self, event):
        '''
        Key press handler.
        @param event: The event.
        '''
        
        touche = event.GetKeyCode()
        if touche == wx.WXK_DELETE:
            self.DeleteSelectedLines()
        # elif touche in [wx.WXK_NUMPAD_ENTER]:
            # self.OpenSelectedLines()
    
    
    def OnItemRightClick(self, event):
        '''
        Right click handler.
        @param event: The event.
        '''
        ligne = event.GetIndex()
        relPath = self.GetPath(index=ligne)
        if self.basePath_src is None:
            srcObj = None
        else:
            srcObj = os.path.join(self.basePath_src, relPath)
        if self.basePath_tgt is None:
            tgtObj = None
        else:
            tgtObj = os.path.join(self.basePath_tgt, relPath)
        
        menu = wx.Menu()
        
        # Supprimer la ligne
        mItem_supLine = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text='Supprimer la ligne')
        self.Bind(event=wx.EVT_MENU,
                   handler=lambda(event):
                                 self.DeleteItem(item=ligne),
                   source=mItem_supLine)
        menu.AppendItem(item=mItem_supLine)
        
        # Menu de la source
        if srcObj is not None and os.path.exists(srcObj):
            # - séparateur
            menu.AppendSeparator()
            # - aller à la source
            mItem_goSrc = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Ouvrir l'emplacement de la source")
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.AllerA(os.path.dirname(srcObj)),
                       source=mItem_goSrc)
            menu.AppendItem(item=mItem_goSrc)
            # - supprimer la cible
            mItem_supSrc = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text='Supprimer la source')
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.SupprimerSrc(relPath=relPath, index=ligne),
                       source=mItem_supSrc)
            menu.AppendItem(item=mItem_supSrc)
        
        # Menu de la cible
        if tgtObj is not None and os.path.exists(tgtObj):
            # - séparateur
            menu.AppendSeparator()
            # - supprimer la cible
            mItem_goTgt = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Ouvrir l'emplacement de la cible")
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.AllerA(os.path.dirname(tgtObj)),
                       source=mItem_goTgt)
            menu.AppendItem(mItem_goTgt)
            # - aller à la cible
            mItem_supTgt = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text='Supprimer la cible')
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.SupprimerTgt(relPath=relPath, index=ligne),
                       source=mItem_supTgt)
            menu.AppendItem(item=mItem_supTgt)
        
        self.PopupMenu(menu)
    
    
    def AllerA(self, path):
        '''
        @brief Ouvrir une fenètre d'exploration Windows dans le répertoire spécifié.
        
        @param path Chemin du répertoire
        '''
        
        try:
            # Tests
            # - cible existante
            if not os.path.exists(path):
                raise ValueError('Répertoire inexistant')
            # - répertoire correct
            if not os.path.isdir(path):
                raise ValueError('Cible incorrecte')
            
            cmd = 'explorer "%s"' % path
            os.system(cmd)
        except Exception, err:
            wx.MessageDialog(self, str(err), 'Erreur', wx.OK | wx.ICON_EXCLAMATION).ShowModal()
    
    
    def SupprimerSrc(self, relPath, index):
        '''
        @brief Supprimer le fichier ou répertoire source spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire source à supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join(self.basePath_src, relPath)
        tgtObj = os.path.join(self.basePath_tgt, relPath)
        
        try:
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression:
                mDialog = wx.MessageDialog(self, 'Voulez-vous vraiment supprimer la source ?', 'Supprimer source', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
            # Supprimer la source
            rm(srcObj)
            
            if not os.path.exists(tgtObj):
                # Supprimer la ligne
                self.DeleteItem(item=index)
            else:
                # Mettre à jour la ligne
                extension = get_extension(tgtObj)
                indiceImage = self.GetIndiceImage(extension)
                self.SetStringItem(index=index, col=MyListCtrl._PATH, label=relPath, imageId=indiceImage)
                if extension == 'folder':
                    self.SetStringItem(index=index, col=MyListCtrl._EXTENSION, label='')
                else:
                    self.SetStringItem(index=index, col=MyListCtrl._EXTENSION, label=extension)
                self.SetStringItem(index=index, col=MyListCtrl._ACTION, label=_SUPPRESSION)
        except Exception, err:
            wx.MessageDialog(self, str(err), 'Erreur', wx.OK | wx.ICON_EXCLAMATION).ShowModal()
    
    
    def SupprimerTgt(self, relPath, index):
        '''
        @brief Supprimer le fichier ou répertoire cible spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire cible à supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join(self.basePath_src, relPath)
        tgtObj = os.path.join(self.basePath_tgt, relPath)
        
        try:
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression:
                mDialog = wx.MessageDialog(self, 'Voulez-vous vraiment supprimer la cible ?', 'Supprimer cible', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
            # Supprimer la source
            rm(tgtObj)
            
            if not os.path.exists(srcObj):
                # Supprimer la ligne
                self.DeleteItem(item=index)
            else:
                # Mettre à jour la ligne
                extension = get_extension(srcObj)
                indiceImage = self.GetIndiceImage(extension)
                self.SetStringItem(index=index, col=MyListCtrl._PATH, label=relPath, imageId=indiceImage)
                self.SetStringItem(index=index, col=MyListCtrl._EXTENSION, label=extension)
                self.SetStringItem(index=index, col=MyListCtrl._ACTION, label=_AJOUT)
        except Exception, err:
            wx.MessageDialog(self, str(err), 'Erreur', wx.OK | wx.ICON_EXCLAMATION).ShowModal()



class SynchonizerFrame(wx.Frame):
    '''Main frame.'''
    
    
    def __init__(self):
        '''Constructeur.'''
        
        self.stop = False  # TODO ?
        self.thread_analyze = None
        self.thread_maj = None
        
        # Frame
        # - Application
        wx.Frame.__init__ (self, None, title='Synchonizer', size=(500, 700))
        self.SetMinSize((300, 500))
        self.CenterOnScreen()
        # - Preferences
        self.preferences = Preferences(self)
        
        # Menu bar
        menuBar = wx.MenuBar()
        self.SetMenuBar(menuBar)
        # - File
        menuBar_file = wx.Menu()
        menuBar.Append(menuBar_file, '&File')
        #     * Exit
        menuBar_file_exit = wx.MenuItem(menuBar_file, wx.ID_ANY, '&Exit\tAlt-F4')
        menuBar_file_exit.SetBitmap(wx.Bitmap('icons/exit.png', wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, lambda event: self.Close(), menuBar_file_exit)
        menuBar_file.AppendItem(menuBar_file_exit)
        # - Action
        menuBar_action = wx.Menu()
        menuBar.Append(menuBar_action, 'Action')
        #     * Stop
        self.menuBar_action_stop = wx.MenuItem(menuBar_action, wx.ID_ANY, 'Stop')
        self.menuBar_action_stop.Enable(False)
        self.menuBar_action_stop.SetBitmap(wx.Bitmap('icons/stop.png', wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, lambda event: self.Stop(), self.menuBar_action_stop)
        menuBar_action.AppendItem(self.menuBar_action_stop)
        #     * Analyze
        self.menuBar_action_analyze = wx.MenuItem(menuBar_action, wx.ID_ANY, 'Analyze')
        self.menuBar_action_analyze.SetBitmap(wx.Bitmap('icons/analyze.png', wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, lambda event: self.OnAnalyze(), self.menuBar_action_analyze)
        menuBar_action.AppendItem(self.menuBar_action_analyze)
        #     * Run
        self.menuBar_action_run = wx.MenuItem(menuBar_action, wx.ID_ANY, 'Run')
        self.menuBar_action_run.SetBitmap(wx.Bitmap('icons/execute.png', wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, lambda event: self.OnExecute(), self.menuBar_action_run)
        menuBar_action.AppendItem(self.menuBar_action_run)
        # - Utils
        menuBar_utils = wx.Menu()
        menuBar.Append(menuBar_utils, '&Utils')  # TODO: rename
        #     * Préférences
        menuBar_utils_preference = wx.MenuItem(menuBar_utils, wx.ID_ANY, 'Preferences')
        menuBar_utils_preference.SetBitmap(wx.Bitmap('icons/preferences.png', wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, self.OnMenu_utils_preferences, menuBar_utils_preference)
        menuBar_utils.AppendItem(menuBar_utils_preference)
        # - Help
        menuBar_help = wx.Menu()
        menuBar.Append(menuBar_help, '&?')
        #     * About
        menuBar_help_about = wx.MenuItem(menuBar_help, wx.ID_ANY, 'About')
        self.Bind(wx.EVT_MENU, self.OnMenu_help_about, menuBar_help_about)
        menuBar_help.AppendItem(menuBar_help_about)
        
        # Panel & Sizer
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer_frame)
        self.panel_fenetre = wx.Panel(self)
        sizer_frame.Add(self.panel_fenetre, 1, wx.EXPAND, 5)
        self.sizer_panel = wx.BoxSizer(wx.VERTICAL)
        self.panel_fenetre.SetSizer(self.sizer_panel)
        
        # Tool bar
        self.tBar = wx.ToolBar(self.panel_fenetre, style=wx.TB_FLAT)
        self.sizer_panel.Add(self.tBar, flag=wx.EXPAND)
        # - Exit
        tool_exit = self.tBar.AddLabelTool(wx.ID_ANY, 'Exit', wx.Bitmap('icons/exit.png', wx.BITMAP_TYPE_PNG), shortHelp='Exit')
        self.tBar.Bind(wx.EVT_TOOL, lambda event: self.Close(), tool_exit)
        # |
        self.tBar.AddSeparator()
        # - Delete selected lines
        tool_deleteSelectedLines = self.tBar.AddLabelTool(wx.ID_ANY, 'Delete selected lines', wx.Bitmap('icons/delete.png', wx.BITMAP_TYPE_PNG), shortHelp='Delete selected liness')
        self.tBar.Bind(wx.EVT_TOOL, lambda event: self.lCtrl.DeleteSelectedLines(), tool_deleteSelectedLines)
        # |
        self.tBar.AddSeparator()
        # - Stop
        self.tool_stop = self.tBar.AddLabelTool(wx.ID_ANY, 'Stop', wx.Bitmap('icons/stop.png', wx.BITMAP_TYPE_PNG), shortHelp='Stop')
        self.tBar.Bind(wx.EVT_TOOL, lambda event: self.Stop(), self.tool_stop)
        # - Analyse
        self.tool_analyse = self.tBar.AddLabelTool(wx.ID_ANY, 'Analyse', wx.Bitmap('icons/analyze.png', wx.BITMAP_TYPE_PNG), shortHelp='Analyze')
        self.tBar.Bind(wx.EVT_TOOL, lambda event: self.OnAnalyze(), self.tool_analyse)
        # - Execute
        self.tool_execute = self.tBar.AddLabelTool(wx.ID_ANY, 'Execture', wx.Bitmap('icons/execute.png', wx.BITMAP_TYPE_PNG), shortHelp='Execute')
        self.tBar.Bind(wx.EVT_TOOL, lambda event: self.Run(), self.tool_execute)
        # 
        self.tBar.Realize()
        
        # _____
        ligne_titre_options = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(ligne_titre_options, flag=wx.ALL | wx.EXPAND, border=5)
        # Options
        # - Title
        sText_options = wx.StaticText(self.panel_fenetre, label='Options')
        font_titre_options = wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        sText_options.SetFont(font_titre_options)
        self.sizer_panel.Add(sText_options, flag=wx.ALL, border=5)
        # - Sizer
        gSizer_options = wx.GridSizer(cols=3)
        self.sizer_panel.Add(gSizer_options, flag=wx.ALL | wx.EXPAND, border=5)
        #     * Input title
        sText_src = wx.StaticText(self.panel_fenetre, label='Input folder:')
        gSizer_options.Add(sText_src, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #     * Input value
        self.tCtrl_src = wx.TextCtrl(self.panel_fenetre, style=wx.TE_READONLY)
        gSizer_options.Add(self.tCtrl_src, flag=wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border=5)
        #     * Input browse
        self.button_src = wx.Button(self.panel_fenetre, label='Browse')
        self.button_src.Bind(wx.EVT_BUTTON, lambda event: self.BrowseSrc())
        gSizer_options.Add(self.button_src, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #     * Target title
        sText_tgt = wx.StaticText(self.panel_fenetre, label='Target folder:')
        gSizer_options.Add(sText_tgt, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #     * Target value
        self.tCtrl_tgt = wx.TextCtrl(self.panel_fenetre, style=wx.TE_READONLY)
        gSizer_options.Add(self.tCtrl_tgt, flag=wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border=5)
        #     * Target browse
        self.button_tgt = wx.Button(self.panel_fenetre, label='Browse')
        self.button_tgt.Bind(wx.EVT_BUTTON, lambda event: self.BrowseTgt())
        gSizer_options.Add(self.button_tgt, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        # _____
        ligne_options_modifications = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(ligne_options_modifications, flag=wx.ALL | wx.EXPAND, border=5)
        # Actions
        # Title
        sText_modifications = wx.StaticText(self.panel_fenetre, label='Modifications:')
        font_titre_modifications = wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        sText_modifications.SetFont(font_titre_modifications)
        self.sizer_panel.Add(sText_modifications, flag=wx.ALL, border=5)
        # List
        self.lCtrl = MyListCtrl(self.panel_fenetre)
        self.sizer_panel.Add(self.lCtrl, 1, wx.ALL | wx.EXPAND, 5)
        # _____
        self.ligne_modifications_actions = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(self.ligne_modifications_actions, flag=wx.ALL | wx.EXPAND, border=5)
        # Loading bar
        self.chargement = wx.Gauge(self.panel_fenetre)
        self.sizer_panel.Add(self.chargement, 0, wx.ALL | wx.EXPAND, 5)
        
        # Events
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        self.init()  # TODO: delete me
        
        # Disable actions
        self.tool_analyse.Enable(False)
        self.tool_execute.Enable(False)
        self.tool_stop.Enable(True)
    
    
    # TODO: delete me
    def init(self):
        if os.path.exists('../tests/Cas_test'):
            shutil.rmtree('../tests/Cas_test')
        shutil.copytree('../tests/Cas_test_sauv', '../tests/Cas_test')
        self.tCtrl_src.SetValue('../tests/Cas_test/src')
        self.tCtrl_tgt.SetValue('../tests/Cas_test/tgt')
    
    
    def OnClose(self, event):
        '''
        Handling the frame closing event.
        @param event: The event.
        '''
        
        if self.preferences.confirmationExit:
            # Analyse en cours
            if self.thread_analyze is not None:
                mDialog = wx.MessageDialog(self, 'Analyse en cours. êtes-vous sûr de vouloir exit ?', 'Exit', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
            # Mise à jour en cours
            elif self.thread_maj is not None:
                mDialog = wx.MessageDialog(self, 'Mise à jour en cours. êtes-vous sûr de vouloir exit ?', 'Exit', wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
        
        self.stop = True
        # while self.thread_analyse is not None:
            # pass
        # while self.thread_maj is not None:
            # pass
        
        self.preferences.Destroy()
        event.Skip()
    
    
    def Stop(self):
        '''Stop the analyze or running.'''
        if self.analyzer is not None:
            self.analyzer.stop()
            self.analyzer.join()
        self.stop = True
    
    
    def OnMenu_utils_preferences(self, event):
        '''
        Handling the "Utils">"Préférences" menu event.
        @param event: The event.
        '''
        self.preferences.Show()
        event.Skip()
    
    
    def OnMenu_help_about(self, event):
        '''
        Handling the "Help">"About" menu event.
        @param event: The event.
        '''
        # TODO: implement
        pass
    
    
    def PathChanged(self):
        '''
        Source or target folder changed.
        Reset the list control.
        '''
        self.lCtrl.basePath_src = self.tCtrl_src.Value
        self.lCtrl.basePath_tgt = self.tCtrl_tgt.Value
        self.lCtrl.DeleteAllItems()
    
    
    def BrowseSrc(self):
        '''Browse the source folder handler.'''
        
        dDialog = wx.DirDialog(self.panel_fenetre, 'Input folder', style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dDialog.ShowModal() != wx.ID_OK: return
        if os.path.samefile(dDialog.Path, self.tCtrl_src.Value): return
        
        self.tCtrl_src.Value = dDialog.Path
        if os.path.samefile(self.tCtrl_src.Value, self.tCtrl_tgt.Value): self.tCtrl_tgt.Value = None
        
        self.PathChanged()
    
    
    def BrowseTgt(self):
        '''Browse the source folder handler.'''
        
        dDialog = wx.DirDialog(self.panel_fenetre, 'Target folder', style=wx.DD_DEFAULT_STYLE)
        if dDialog.ShowModal() != wx.ID_OK: return
        if os.path.samefile(dDialog.Path, self.tCtrl_tgt.Value): return
        
        self.tCtrl_tgt.Value = dDialog.Path
        if os.path.samefile(self.tCtrl_src.Value, self.tCtrl_tgt.Value): self.tCtrl_src.Value = None
        
        self.PathChanged()
    
    
    def OnAnalyze(self):
        '''Analyze folders.'''
        
        self._disableActionButtons()
        
        self.lCtrl.DeleteAllItems()
        
        # Thread
        self.analyzer = action.Analyzer(self.tCtrl_src.Value, self.tCtrl_tgt.Value)
        self.analyzer.handler = lambda action: self.lCtrl.Add(action)
        self.analyzer.after = self._onAnalyzeTerminated
        self.analyzer.start()
    
    
    def _onAnalyzeTerminated(self):
        '''Analyze terminated.'''
        self._enableActionButtons()
        self.analyzer = None
    
    
    def OnExecute(self):
        '''Execute actions.'''
        
        self._disableActionButtons()
        
        # Thread
        self.thread_maj = threading.Thread(target=self._onExecuteThread, name='Mise à jour des fichiers')
        self.thread_maj.start()
    
    
    def _onExecuteThread(self):
        '''Thread who execute actions.'''
        
        self.chargement.SetRange(len(self.lCtrl.actions))
        self.chargement.SetValue(0)
        
        while len(self.lCtrl.actions) >= 1:
            if self.stop: break
            
            action = self.lCtrl.actions[0]
            action.execute()
            self.lCtrl.DeleteLine(0)
            self.chargement.Value += 1
        
        self._enableActionButtons()
        
        self.stop = False
        self.thread_maj = None
    
    
    def _enableActionButtons(self):
        self.tool_stop.Enable(False)
        self.tool_analyse.Enable(True)
        self.tool_execute.Enable(True)
    
    
    def _disableActionButtons(self):
        self.tool_analyse.Enable(False)
        self.tool_execute.Enable(False)
        self.tool_stop.Enable(True)



class Preferences(wx.Frame):
    '''Preferences frame.'''
    
    
    def __init__(self, parent):
        '''
        Constructeur.
        @param parent: The parent frame.
        '''
        
        # Préférences du programme
        self.confirmationExit = True
        self.confirmationSuppression = True
        self.supprimerCible = True
        self.ignorerCiblePlusRecente = True
        
        # Fenêtre
        sizeFenetre = wx.Size(w=275, h=150)
        wx.Frame.__init__ (self, parent, title='Préférences', size=sizeFenetre)
        self.SetSizeHints(minW=sizeFenetre.GetWidth(), minH=sizeFenetre.GetHeight(), maxW=sizeFenetre.GetWidth(), maxH=sizeFenetre.GetHeight())
        
        #     Sizer de la fenêtre
        self.sizer_frame = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer_frame)
        
        #         Panel général
        self.panel_fenetre = wx.Panel(self)
        self.sizer_frame.Add(self.panel_fenetre, 1, wx.EXPAND, 5)
        
        #             Sizer du panel général
        self.sizer_panel = wx.BoxSizer(orient=wx.VERTICAL)
        self.panel_fenetre.SetSizer(sizer=self.sizer_panel)
        
        #                 Titre fenêtre
        sText_titre = wx.StaticText(self.panel_fenetre, label='Paramètres')
        font_titre = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        sText_titre.SetFont(font_titre)
        self.sizer_panel.Add(sText_titre, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border=5)
        
        #                 Ligne séparatrice
        ligne_titre_options = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(ligne_titre_options, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                     Demande de confirmation de suppression
        self.cBox_confirmationSuppression = wx.CheckBox(self.panel_fenetre, label=' Demande de confirmation de suppression')
        self.cBox_confirmationSuppression.SetValue(self.confirmationSuppression)
        self.cBox_confirmationSuppression.Bind(wx.EVT_CHECKBOX, self.OnCheckBox_confirmationSuppression)
        self.sizer_panel.Add(self.cBox_confirmationSuppression, flag=wx.ALL, border=5)
        #                     Supprimer cible si la source n'existe pas
        self.cBox_supprimerCible = wx.CheckBox(self.panel_fenetre, label=" Supprimer la cible si la source n'existe pas")
        self.cBox_supprimerCible.SetValue(self.supprimerCible)
        self.cBox_supprimerCible.Bind(wx.EVT_CHECKBOX, self.OnCheckBox_supprimerCible)
        self.sizer_panel.Add(self.cBox_supprimerCible, flag=wx.ALL, border=5)
        #                     Ignorer les cibles plus récentes
        self.cBox_ignorerCiblePlusRecente = wx.CheckBox(self.panel_fenetre, label=' Ignorer les cibles plus récentes que les sources')
        self.cBox_ignorerCiblePlusRecente.SetValue(self.ignorerCiblePlusRecente)
        self.cBox_ignorerCiblePlusRecente.Bind(wx.EVT_CHECKBOX, self.OnCheckBox_ignorerCiblePlusRecente)
        self.sizer_panel.Add(self.cBox_ignorerCiblePlusRecente, flag=wx.ALL, border=5)
        
        self.Bind(wx.EVT_CLOSE, lambda event: self.Hide())
    
    
    def OnCheckBox_confirmationSuppression(self, event):
        '''
        @brief Clic sur la case "Demande de confirmation de suppression".
        @param event: The event.
        '''
        self.confirmationSuppression = self.cBox_confirmationSuppression.IsChecked()
        event.Skip()
    
    
    def OnCheckBox_supprimerCible(self, event):
        '''
        @brief Clic sur la case "Supprimer la cible si la source n'existe pas".
        @param event: Evémenement
        '''
        self.supprimerCible = self.cBox_supprimerCible.IsChecked()
        event.Skip()
    
    
    def OnCheckBox_ignorerCiblePlusRecente(self, event):
        '''
        @brief Clic sur la case " Ignorer les cibles plus récentes que les sources".
        @param event: Evémenement
        '''
        self.ignorerCiblePlusRecente = self.cBox_ignorerCiblePlusRecente.IsChecked()
        event.Skip()



if __name__ == '__main__':
    ex = wx.App(redirect=False)
    fen = SynchonizerFrame()
    fen.Show(True)
    # fen.CenterOnScreen()
    ex.MainLoop()
