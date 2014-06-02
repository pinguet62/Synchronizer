#!/usr/bin/python
# -*- coding: utf-8 -*-


'''Synchronise two folders.'''


# TODO: wx.ID_ANY


__author__ = __maintainer__ = "Pinguet62"
__date__ = "2014/06/02"
__email__ = "pinguet62@gmail.com"
__license__ = "Creative Commons, Attribution NonCommercial ShareAlike, 4.0"
__status__ = "Develpment"
__version__ = "2.0"


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


def get_size(path):
    '''
    @brief Obtenir la taille de la cible.
    
    @patam path Chemin de la cible
    
    @return Taille en octet
    '''
    
    if os.path.isdir(path):
        size = 0
        for root, dirs, files in os.walk(path):
            for fich in files:
                size += os.path.getsize(os.path.join(root, fich))
    else:
        size = os.path.getsize(path)
    
    return size



def octetToHumainSize(size):
    '''
    @brief Convertir la taille en octet vers une mesure compréhensible par l'humain.
    
    @param size Taille en octet
    
    @return String représentant la taille (1 d�cimales près)
    '''
    
    if size == "":
        return ""
    
    # o
    if size < 1024 ** 1:
        return "%do" % size
    # ko
    elif size < 1048576:
        return "%.1fko" % (size / 1024)
    # Mo
    elif size < 1073741824:
        return "%.1fMo" % (size / 1048576)
    # Go
    elif size < 1099511627776:
        return "%.1fGo" % (size / 1073741824)
    # To
    else:
        return "%.1fTo" % (size / 1099511627776)



def get_extension(path):
    '''
    @brief Obtenir le type de la cible.
    
    @param path Chemin de la cible
    
    @return Son extension s'il s'agit d'un fichier, "folder" s'il s'agit d'un répertoire
    '''
    
    if os.path.isdir(path):
        return "folder"
    elif os.path.isfile(path):
        return os.path.splitext(path)[1].lower()
    else:
        return ""



def extension_to_bitmap(extension):
    '''
    @brief Obtenir l'image correspondante à l'extension.
    
    @param extension Extension
    
    @return Image correspondante
    '''
    
    # Type répertoire
    if extension == "folder":
        bm = wx.Bitmap(name="icons/folder.png", type=wx.BITMAP_TYPE_PNG)
        bm.SetSize((16, 16))
        return bm
    
    
    flags = win32com.shell.shellcon.SHGFI_SMALLICON | win32com.shell.shellcon.SHGFI_ICON | win32com.shell.shellcon.SHGFI_USEFILEATTRIBUTES
    
    retval, info = win32com.shell.shell.SHGetFileInfo(extension,
                                                       win32con.FILE_ATTRIBUTE_NORMAL,
                                                       flags)
    
    assert retval
    
    hicon, iicon, attr, display_name, type_name = info
    
    icon = wx.EmptyIcon()
    icon.SetHandle(hicon)
    return wx.BitmapFromIcon(icon)



def copy(src, tgt):
    '''
    @brief Copier de fichier ou répertoire.
    
    @param src Chemin de la source
    @param tgt Chemin de la cible
    '''
    
    # Supprimer la cible existante
    if os.path.exists(tgt):
        rm(tgt)
    
    # Copier
    if os.path.isdir(src):
        shutil.copytree(src, tgt)
    else:
        shutil.copy2(src, tgt)



def rm(path):
    '''
    @brief Supprimer la cible.
    
    @param Chemin du fichier ou du répertoire
    '''
    
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    
    # Vérifications
    if os.path.exists(path):
        raise Exception("Echec de la suppression")



# Action sur les fichiers
_AJOUT = "ajout"  # Ajouter au répertoire cible
_MISEAJOUR = "mise a jour"  # Mettre à jour la cible
_REMPLACEMENT = "remplacement"  # Remplacer le répertoire cible par le fichier source, ou remplacer le fichier cible par le répertoire source
_SUPPRESSION = "suppression"  # Supprimer la cible



class MyListCtrl(wx.ListCtrl):
    '''
    @class MyListCtrl
    @brief Redéfinition de la classe ListCtrl.
    @details Compl�te la classe ListCtrl en lui ajoutant des méthodes utiles à l'application.
    @author Pinguet
    @version 1
    '''
    
    
    
    # Colonnes
    _PATH = 0
    _EXTENSION = 1
    _ACTION = 2
    _TAILLE = 3
    
    
    
    def __init__(self, parent):
        '''
        @brief Constructeur.
        
        @param parent Objet parent
        '''
        
        self.basePath_src = None
        self.basePath_tgt = None
        
        # Constructeurs parents
        wx.ListCtrl.__init__(self, parent=parent, style=wx.LC_REPORT)
        
        # Noms de colonne
        self.InsertColumn(col=MyListCtrl._PATH, heading="Path", width=200)
        self.InsertColumn(col=MyListCtrl._EXTENSION, heading="Extension", width=65)
        self.InsertColumn(col=MyListCtrl._ACTION, heading="Action", width=89)
        self.InsertColumn(col=MyListCtrl._TAILLE, heading="Taille", width=60)
        
        # Icons
        self.listeImages = wx.ImageList(width=16, height=16)
        self.extension_indiceImage = {}  # Dictionnaire: extension du fichier -> indice de l'image
        
        # Evénements
        self.Bind(event=wx.EVT_LIST_ITEM_RIGHT_CLICK, handler=self.OnListItemRightClick)
        self.Bind(event=wx.EVT_LIST_KEY_DOWN, handler=self.OnListKeyDown)
    
    
    
    ####################################################################################################
    # Divers
    ####################################################################################################
    
    def SetBasePath(self, src=None, tgt=None):
        '''
        @param Définir le répertoire de base.
        
        @param src Répertoire source de base
        @param tgt Répertoire cible de base
        
        @exception ValueError Répertoire inexistant
        '''
        
        if src is not None:
            self.basePath_src = src
        if tgt is not None:
            self.basePath_tgt = tgt
    
    
    
    def GetIndiceImage(self, extension=""):
        '''
        @brief Obtenir l'indice de l'image � partir de son extension.
        
        @param extension Extension
        
        @return Indice de l'image dans la liste
        '''
        
        # Extension connue
        if extension in self.extension_indiceImage:
            return self.extension_indiceImage[ extension ]
        
        # Nouvelle extension
        # - ajouter la nouvelle image � la ListCtrl
        bmp = extension_to_bitmap(extension)
        indice = self.listeImages.Add(bmp)
        self.SetImageList(self.listeImages, wx.IMAGE_LIST_SMALL)
        # - ajouter l'extension au dictionnaire
        self.extension_indiceImage[ extension ] = indice
        return indice
    
    
    
    ####################################################################################################
    # Modification des lignes
    ####################################################################################################
    
    def DeleteSelectedIndex(self):
        '''
        @brief Supprimer les lignes sélectionnées.
        '''
        
        ligne = self.GetFirstSelected()
        while ligne != -1:
            self.DeleteItem(item=ligne)
            ligne = self.GetFirstSelected()
    
    
    
    def Add(self, relPath="", extension="", action="", size=""):
        '''
        @brief Ajouter une ligne dans la liste.
        
        @param relPath Chemin relatif du fichier ou répertoire
        @param extension Extension du fichier, vide si inconnu, ou "folder" pour un répertoire
        @param action Type de modification
        @param size Taille
        '''
        
        num = self.GetItemCount()
        
        # Image + Path
        indiceImage = self.GetIndiceImage(extension)
        self.InsertStringItem(index=num, label=relPath, imageIndex=indiceImage)
        
        # Extension
        if extension == "folder":
            self.SetStringItem(index=num, col=MyListCtrl._EXTENSION, label="")
        else:
            self.SetStringItem(index=num, col=MyListCtrl._EXTENSION, label=extension)
        
        # Modification
        self.SetStringItem(index=num, col=MyListCtrl._ACTION, label=action)
        
        # Taille
        self.SetStringItem(index=num, col=MyListCtrl._TAILLE, label=octetToHumainSize(size))
    
    
    
    ####################################################################################################
    # Evénements divers
    ####################################################################################################
    
    def OnListKeyDown(self, event):
        '''
        @brief Pression d'une touche.
        
        @param event: Evénement
        '''
        
        touche = event.GetKeyCode()
        if touche == wx.WXK_DELETE:
            if self.GetTopLevelParent().thread_analyze is None and self.GetTopLevelParent().thread_maj is None:
                self.DeleteSelectedIndex()
        # elif touche in [ wx.WXK_NUMPAD_ENTER ]:
            # self.OpenSelectedLines()
    
    
    
    def OnListItemRightClick(self, event):
        '''
        @brief Clic droit sur une ligne.
        
        @param event: Evénement
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
        mItem_supLine = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Supprimer la ligne")
        self.Bind(event=wx.EVT_MENU,
                   handler=lambda(event):
                                 self.DeleteItem(item=ligne),
                   source=mItem_supLine)
        menu.AppendItem(item=mItem_supLine)
        
        # Menu de la source
        if srcObj is not None and os.path.exists(srcObj):
            # - séparateur
            menu.AppendSeparator()
            # - aller � la source
            mItem_goSrc = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Ouvrir l'emplacement de la source")
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.AllerA(os.path.dirname(srcObj)),
                       source=mItem_goSrc)
            menu.AppendItem(item=mItem_goSrc)
            # - supprimer la cible
            mItem_supSrc = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Supprimer la source")
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
            menu.AppendItem(item=mItem_goTgt)
            # - aller � la cible
            mItem_supTgt = wx.MenuItem(parentMenu=menu, id=wx.ID_ANY, text="Supprimer la cible")
            self.Bind(event=wx.EVT_MENU,
                       handler=lambda(event):
                                     self.SupprimerTgt(relPath=relPath, index=ligne),
                       source=mItem_supTgt)
            menu.AppendItem(item=mItem_supTgt)
        
        self.PopupMenu(menu=menu)
    
    
    
    ####################################################################################################
    # Actions du menu
    ####################################################################################################
    
    def AllerA(self, path):
        '''
        @brief Ouvrir une fenètre d'exploration Windows dans le répertoire spécifié.
        
        @param path Chemin du répertoire
        '''
        
        try:
            # Tests
            # - cible existante
            if not os.path.exists(path):
                raise ValueError("Répertoire inexistant")
            # - répertoire correct
            if not os.path.isdir(path):
                raise ValueError("Cible incorrecte")
            
            cmd = 'explorer "%s"' % path
            os.system(cmd)
        except Exception, err:
            wx.MessageDialog(self, str(err), "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
    
    
    
    def SupprimerSrc(self, relPath, index):
        '''
        @brief Supprimer le fichier ou répertoire source spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire source � supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join(self.basePath_src, relPath)
        tgtObj = os.path.join(self.basePath_tgt, relPath)
        
        try:
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression:
                mDialog = wx.MessageDialog(self, "Voulez-vous vraiment supprimer la source ?", "Supprimer source", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
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
                if extension == "folder":
                    self.SetStringItem(index=index, col=MyListCtrl._EXTENSION, label="")
                else:
                    self.SetStringItem(index=index, col=MyListCtrl._EXTENSION, label=extension)
                self.SetStringItem(index=index, col=MyListCtrl._ACTION, label=_SUPPRESSION)
        except Exception, err:
            wx.MessageDialog(self, message=str(err), "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
    
    
    
    def SupprimerTgt(self, relPath, index):
        '''
        @brief Supprimer le fichier ou répertoire cible spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire cible � supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join(self.basePath_src, relPath)
        tgtObj = os.path.join(self.basePath_tgt, relPath)
        
        try:
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression:
                mDialog = wx.MessageDialog(self, "Voulez-vous vraiment supprimer la cible ?", "Supprimer cible", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
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
            wx.MessageDialog(self, str(err), "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
    
    
    
    ####################################################################################################
    # Informations sur les lignes
    ####################################################################################################
    
    def GetPath(self, index):
        '''
        @brief Obtenir le chemin de la ligne.
        
        @param index Numéro de ligne
        
        @return Chemin
        '''
        
        path = self.GetItem(itemId=index, col=MyListCtrl._PATH).GetText()
        # return str( path )
        return path
    
    
    
    def GetExtention(self, index):
        '''
        @brief Obtenir l'extension de la ligne.
        
        @param index Numéro de ligne
        
        @return Extension
        '''
        
        extension = self.GetItem(itemId=index, col=MyListCtrl._EXTENSION).GetText()
        # return str( extension )
        return extension
    
    
    
    def GetAction(self, index):
        '''
        @brief Obtenir l'action � effectuer de la ligne.
        
        @param index Numéro de ligne
        
        @return Action
        '''
        
        action = self.GetItem(itemId=index, col=MyListCtrl._ACTION).GetText()
        # return str( action )
        return action
    
    
    def GetSize(self, index):
        '''
        @brief Obtenir la taille de la ligne.
        
        @param index Numéro de ligne
        
        @return Taille
        '''
        
        taille = self.GetItem(itemId=index, col=MyListCtrl._TAILLE).GetText()
        return taille


class SynchonizerFrame(wx.Frame):
    '''Main frame.'''
    
    
    def __init__(self):
        '''Constructeur.'''
        
        self.stop = False  # TODO ?
        self.thread_analyze = None
        self.thread_maj = None
        
        # Frame
        #     Application
        wx.Frame.__init__ (self, None, title="Synchonizer", size=(500, 700))
        self.SetMinSize((300, 500))
        self.CenterOnScreen()
        #     Preferences
        self.preferences = Preferences(self)
        
        # Menu bar
        menuBar = wx.MenuBar()
        self.SetMenuBar(menuBar)
        #     File
        menuBar_file = wx.Menu()
        menuBar.Append(menuBar_file, "&File")
        #         Exit
        menuBar_file_exit = wx.MenuItem(menuBar_file, wx.ID_ANY, "&Exit\tAlt-F4")
        menuBar_file_exit.SetBitmap(wx.Bitmap("icons/exit.png", wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, self.OnMenu_file_exit, menuBar_file_exit)
        menuBar_file.AppendItem(menuBar_file_exit)
        #     Action
        menuBar_action = wx.Menu()
        menuBar.Append(menuBar_action, "Action")
        #         Analyze
        self.menuBar_action_analyze = wx.MenuItem(menuBar_action, wx.ID_ANY, "Analyze")
        self.Bind(wx.EVT_MENU, self.OnMenu_action_analyze, self.menuBar_action_analyze)
        menuBar_action.AppendItem(self.menuBar_action_analyze)
        #         Run
        self.menuBar_action_run = wx.MenuItem(menuBar_action, wx.ID_ANY, "Run")
        self.Bind(wx.EVT_MENU, self.OnMenu_action_run, self.menuBar_action_run)
        menuBar_action.AppendItem(self.menuBar_action_run)
        #         Stop
        self.menuBar_action_stop = wx.MenuItem(menuBar_action, wx.ID_ANY, "Stop")
        self.menuBar_action_stop.Enable(False)
        self.Bind(wx.EVT_MENU, self.OnMenu_action_stop, self.menuBar_action_stop)
        menuBar_action.AppendItem(self.menuBar_action_stop)
        #     Utils
        menuBar_utils = wx.Menu()
        menuBar.Append(menuBar_utils, "&Utils")  # TODO: rename
        #         Préférences
        menuBar_utils_preference = wx.MenuItem(menuBar_utils, wx.ID_ANY, "Preferences")
        menuBar_utils_preference.SetBitmap(wx.Bitmap("icons/preferences.png", wx.BITMAP_TYPE_PNG))
        self.Bind(wx.EVT_MENU, self.OnMenu_utils_preferences, menuBar_utils_preference)
        menuBar_utils.AppendItem(menuBar_utils_preference)
        #     Help
        menuBar_help = wx.Menu()
        menuBar.Append(menuBar_help, "&?")
        #         "About"
        menuBar_help_about = wx.MenuItem(menuBar_help, wx.ID_ANY, "About")
        self.Bind(wx.EVT_MENU, self.OnMenu_help_about, menuBar_help_about)
        menuBar_help.AppendItem(menuBar_help_about)
        
        #     Sizer (of frame)
        self.sizer_frame = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer_frame)
        
        #         General panel
        self.panel_fenetre = wx.Panel(self)
        self.sizer_frame.Add(self.panel_fenetre, 1, wx.EXPAND, 5)
        
        #             Sizer (of General panel)
        self.sizer_panel = wx.BoxSizer(wx.VERTICAL)
        self.panel_fenetre.SetSizer(self.sizer_panel)
        
        #                 Tool bar
        self.tBar = wx.ToolBar(self.panel_fenetre, style=wx.TB_FLAT)
        self.sizer_panel.Add(self.tBar, flag=wx.EXPAND)
        #                     Exit
        tool_exit = self.tBar.AddLabelTool(wx.ID_ANY, "Exit", wx.Bitmap("icons/exit.png", wx.BITMAP_TYPE_PNG), shortHelp="Exit")
        self.tBar.Bind(wx.EVT_TOOL, self.OnEventTool_exit, tool_exit)
        # 
        self.tBar.AddSeparator()
        #                     Delete selected lines
        tool_deleteSelectedLines = self.tBar.AddLabelTool(wx.ID_ANY, "Delete selected lines", wx.Bitmap("icons/delete.png", wx.BITMAP_TYPE_PNG), shortHelp='Delete selected liness')
        self.tBar.Bind(wx.EVT_TOOL, self.OnEventTool_deleteSelectedLines, tool_deleteSelectedLines)
        # 
        self.tBar.Realize()
        
        #                 Ligne séparatrice
        ligne_titre_options = wx.StaticLine(parent=self.panel_fenetre)
        self.sizer_panel.Add(ligne_titre_options, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                 Options title
        sText_options = wx.StaticText(self.panel_fenetre, label="Options")
        font_titre_options = wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        sText_options.SetFont(font_titre_options)
        self.sizer_panel.Add(sText_options, flag=wx.ALL, border=5)
        
        #                 Sizer options
        gSizer_options = wx.GridSizer(cols=3)
        self.sizer_panel.Add(gSizer_options, flag=wx.ALL | wx.EXPAND, border=5)
        #                     Input title
        sText_src = wx.StaticText(self.panel_fenetre, label="Input folder:")
        gSizer_options.Add(sText_src, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Input value
        self.tCtrl_src = wx.TextCtrl(self.panel_fenetre, style=wx.TE_READONLY)
        gSizer_options.Add(self.tCtrl_src, flag=wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Input browse
        self.button_src = wx.Button(self.panel_fenetre, label="Browse")
        self.button_src.Bind(wx.EVT_BUTTON, self.OnButtonClick_browseSrc)
        gSizer_options.Add(self.button_src, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Target title
        sText_tgt = wx.StaticText(self.panel_fenetre, label="Target folder:")
        gSizer_options.Add(sText_tgt, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Target value
        self.tCtrl_tgt = wx.TextCtrl(self.panel_fenetre, style=wx.TE_READONLY)
        gSizer_options.Add(self.tCtrl_tgt, flag=wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Target browse
        self.button_tgt = wx.Button(self.panel_fenetre, label="Browse")
        self.button_tgt.Bind(wx.EVT_BUTTON, self.OnButtonClick_browseTgt)
        gSizer_options.Add(self.button_tgt, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        
        #                 Ligne séparatrice
        ligne_options_modifications = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(ligne_options_modifications, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                 Titre modifications
        sText_modifications = wx.StaticText(self.panel_fenetre, label="Modifications:")
        font_titre_modifications = wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        sText_modifications.SetFont(font_titre_modifications)
        self.sizer_panel.Add(sText_modifications, flag=wx.ALL, border=5)
        
        #                 Liste des modifications
        self.lCtrl = MyListCtrl(parent=self.panel_fenetre)
        self.sizer_panel.Add(self.lCtrl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                 Sizer boutons d'action sur la liste
        # bSizer_buttonsListe = wx.BoxSizer( orient = wx.HORIZONTAL )
        # self.sizer_panel.Add( item = bSizer_buttonsListe, flag = wx.ALL | wx.EXPAND, border = 5 )
        #                     Bouton "supprimer la ligne"
        # bm_supprimer = wx.Bitmap( name = "icons/supprimer.png", type = wx.BITMAP_TYPE_ANY )
        # bmButton_supprimer = wx.BitmapButton( self.panel_fenetre, bitmap = bm_supprimer, size = (20,20) )
        # bmButton_supprimer.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_supprimerSelection )
        # bSizer_buttonsListe.Add( item = bmButton_supprimer, flag = wx.ALL, border = 5 )
        
        #                 Ligne séparatrice
        ligne_modifications_actions = wx.StaticLine(self.panel_fenetre)
        self.sizer_panel.Add(ligne_modifications_actions, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                 Sizer actions
        self.bSizer_actions = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.sizer_panel.Add(self.bSizer_actions, flag=wx.ALL | wx.EXPAND, border=5)
        #                     Bouton stop
        self.button_stop = wx.Button(self.panel_fenetre, label="Stop")
        self.button_stop.Show(False)
        self.button_stop.Bind(wx.EVT_BUTTON, self.OnButtonClick_stop)
        self.bSizer_actions.Add(self.button_stop, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Bouton analyze
        self.button_analyze = wx.Button(self.panel_fenetre, label="Analyze")
        self.button_analyze.Bind(wx.EVT_BUTTON, self.OnButtonClick_analyze)
        self.bSizer_actions.Add(self.button_analyze, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        #                     Barre de chargement
        self.chargement = wx.Gauge(self.panel_fenetre)
        self.bSizer_actions.Add(self.chargement, 1, wx.ALL, 5)
        #                     Bouton mise à jour
        self.button_run = wx.Button(self.panel_fenetre, label="Mise à jour")
        self.button_run.Bind(wx.EVT_BUTTON, self.OnButtonClick_run)
        self.bSizer_actions.Add(self.button_run, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        
        # Bouton de test
        button_test = wx.Button(self.panel_fenetre, label="test")
        button_test.Bind(wx.EVT_BUTTON, self.test)
        self.bSizer_actions.Add(button_test, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        
        # Événements
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        self.init()  # TODO: delete me
    
    
    # TODO: delete me
    def init(self):
        if os.path.exists("tests/Cas_test"):
            shutil.rmtree("tests/Cas_test")
        shutil.copytree("tests/Cas_test_sauv", "tests/Cas_test")
        self.tCtrl_src.SetValue("tests/Cas_test\\src")
        self.tCtrl_tgt.SetValue("tests/Cas_test\\tgt")
        self.OnButtonClick_analyze(None)
    
    
    # TODO: delete me
    def test(self, event):
        print octetToHumainSize(1023)
        print octetToHumainSize(1024)
        print octetToHumainSize(1025)
        print octetToHumainSize(2048)
    
    
    def OnClose(self, event):
        '''
        Handling the frame closing event.
        @param event: The event.
        '''
        
        if self.preferences.confirmationExit:
            # Analyse en cours
            if self.thread_analyze is not None:
                mDialog = wx.MessageDialog(self, "Analyse en cours. êtes-vous sûr de vouloir exit ?", "Exit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
            # Mise à jour en cours
            elif self.thread_maj is not None:
                mDialog = wx.MessageDialog(self, "Mise à jour en cours. êtes-vous sûr de vouloir exit ?", "Exit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
                if mDialog.ShowModal() == wx.ID_NO:
                    return
        
        self.stop = True
        # while self.thread_analyse is not None:
            # pass
        # while self.thread_maj is not None:
            # pass
        
        self.preferences.Destroy()
        event.Skip()
    
    
    def OnMenu_file_exit(self, event):
        '''
        Handling the "File">"Exit" menu event.
        @param event: The event.
        '''
        self.Close()
    
    
    def OnMenu_action_analyze(self, event):
        '''
        Handling the "Action">"Analyze" menu event.
        @param event: The event.
        '''
        self.OnRun_analyze()
    
    
    def OnMenu_action_run(self, event):
        '''
        Handling the "Action">"Run" menu event.
        @param event: The event.
        '''
        self.OnRun_run()
    
    
    def OnMenu_action_stop(self, event):
        '''
        Handling the "Action">"Stop" menu event.
        @param event: The event.
        '''
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
    
    
    def OnEventTool_exit(self, event):
        '''
        Handling the "Exit" toolbar event.
        @param event: The event.
        '''
        self.Close()
    
    
    def OnEventTool_deleteSelectedLines(self, event):
        '''
        Handling the "Delete selected lines" toolbar event.
        @param event: The event.
        '''
        self.lCtrl.DeleteSelectedIndex()
    
    
    def OnButtonClick_browseSrc(self, event):
        '''
        Handling the "Browse" input button clicking event.
        @param event: The event.
        '''
        
        dDialog = wx.DirDialog(self.panel_fenetre, "Input folder", style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dDialog.ShowModal() != wx.ID_OK:
            return
        
        path = dDialog.Path
        if path == self.tCtrl_src.Value:  # TODO: os.path.same
            return
        if path == self.tCtrl_tgt.Value:  # TODO: os.path.same
            self.tCtrl_tgt.Value = ""
        
        # TODO
        self.tCtrl_src.Value = path
        self.lCtrl.SetBasePath(src=self.tCtrl_src.Value, tgt=self.tCtrl_tgt.Value)
        self.lCtrl.DeleteAllItems()
    
    
    def OnButtonClick_browseTgt(self, event):
        '''
        Handling the "Browse" target button clicking event.
        @param event: The event.
        '''
        
        dDialog = wx.DirDialog(self.panel_fenetre, "Target folder", style=wx.DD_DEFAULT_STYLE)
        if dDialog.ShowModal() != wx.ID_OK:
            return
        
        path = dDialog.Path
        if path == self.tCtrl_tgt.Value:
            return
        # - cible diff�rente de la source
        if path == self.tCtrl_src.Value:
            wx.MessageDialog(self, "The archive folder must be diffrent to the data folder.", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        
        self.tCtrl_tgt.Value = path
        self.lCtrl.SetBasePath(src=self.tCtrl_src.Value, tgt=self.tCtrl_tgt.Value)
        self.lCtrl.DeleteAllItems()
    
    
    def OnButtonClick_supprimerSelection(self, event):
        '''
        Handling the "Delete selected lines" button clicking event.
        @param event: The event.
        '''
        self.lCtrl.DeleteSelectedIndex()
    
    
    def OnButtonClick_stop(self, event):
        '''
        Handling the stopping synchronization.
        @param event: The event.
        '''
        self.stop = True
    
    
    def OnButtonClick_analyze(self, event):
        '''
        Handling the analyzing folders event.
        @param event: The event.
        '''
        self.OnRun_analyze()
    
    
    def OnButtonClick_run(self, event):
        '''
        @brief Clic sur le bouton "Mise à jour".
        @param event: The event.
        '''
        self.OnRun_run()
    
    ####################################################################################################
    # Analyse et mise à jour des fichiers et répertoires
    ####################################################################################################
    
    def OnRun_analyze(self):
        '''
        @brief Analyse des répertoires.
        @details Vérifier les paramètres avant de lancer le thread l'analyse.
        '''
        
        # Tests:
        # - aucune action en cours
        if self.thread_analyze is not None:
            return
        if self.thread_maj is not None:
            return
        # - champs corrects
        if not os.path.isdir(self.tCtrl_src.GetValue()):
            wx.MessageDialog(self, "Répertoire source incorrect", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        if not os.path.isdir(self.tCtrl_tgt.GetValue()):
            wx.MessageDialog(self, "Répertoire cible incorrect", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        if self.tCtrl_src.GetValue() == self.tCtrl_tgt.GetValue():
            wx.MessageDialog(self, "Répertoire identiques", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        
        # D�sactiver les boutons
        self.button_analyze.Show(False)
        self.button_stop.Show(True)
        self.button_run.Enable(False)
        # D�sactiver les menus
        self.menuBar_action_analyze.Enable(False)
        self.menuBar_action_run.Enable(False)
        self.menuBar_action_stop.Enable(True)
        
        # Lancer le thread
        self.thread_analyze = threading.Thread(target=self.OnThread_analyze, name="Analyse des répertoires")
        self.thread_analyze.start()
        # self.OnThread_analyze() # tmp
    
    
    
    def OnThread_analyze(self):
        '''
        @brief Thread d'analyse des répertoires.
        '''
        
        try:
            self.lCtrl.DeleteAllItems()
            
            # Faire l'analyse
            src = self.tCtrl_src.GetValue()
            tgt = self.tCtrl_tgt.GetValue()
            self.analyze(src, tgt)
        except Exception, err:
            wx.MessageDialog(self, str(err), "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
        
        # Activer les boutons
        self.button_analyze.Show(True)
        self.button_stop.Show(False)
        self.button_run.Enable(True)
        self.bSizer_actions.Layout()
        # Activer les menus
        self.menuBar_action_analyze.Enable(True)
        self.menuBar_action_run.Enable(True)
        self.menuBar_action_stop.Enable(False)
        
        self.stop = False
        self.thread_analyze = None
    
    
    
    def analyze(self, src, tgt):
        '''
        @brief Comparaison et analyse des 2 cibles.
        @remark Fonction r�cursive.
        
        @param src Chemin absolu du répertoire source
        @param tgt Chemin absolu du répertoire cible
        '''
        
        # Analyser la source
        for obj in os.listdir(src):
            # Stop
            if self.stop == True:
                return
            
            srcObj = os.path.join(src, obj)
            tgtObj = os.path.join(tgt, obj)
            relpathObj = os.path.relpath(srcObj, self.tCtrl_src.GetValue())
            
            # src = fichier
            if os.path.isfile(srcObj):
                # tgt inexistant: Copier
                if not os.path.exists(tgtObj):
                    self.lCtrl.Add(relPath=relpathObj, action=_AJOUT, extension=get_extension(srcObj), size=get_size(srcObj))
                # tgt fichier: Comparer dates + remplacer
                elif os.path.isfile(tgtObj):
                    if os.path.getmtime(tgtObj) + 0.0001 < os.path.getmtime(srcObj):
                        self.lCtrl.Add(relPath=relpathObj, action=_MISEAJOUR, extension=get_extension(srcObj), size=get_size(srcObj))
                    if not self.preferences.ignorerCiblePlusRecente:
                        if os.path.getmtime(tgtObj) > os.path.getmtime(srcObj) + 0.0001:
                            self.lCtrl.Add(relPath=relpathObj, action=_MISEAJOUR, extension=get_extension(srcObj), size=get_size(srcObj))
                # tgt répertoire: Remplacer tgt par src
                elif os.path.isdir(tgtObj):
                    self.lCtrl.Add(relPath=relpathObj, action=_REMPLACEMENT, extension=get_extension(srcObj), size=get_size(srcObj))
                # tgt de type inconnu
                else:
                    print "Cible de type inconnu: %s" % tgtObj
            # src = répertoire
            elif os.path.isdir(srcObj):
                # tgt inexistant: Copier
                if not os.path.exists(tgtObj):
                    self.lCtrl.Add(relPath=relpathObj, action=_AJOUT, extension="folder", size=get_size(srcObj))
                # tgt fichier: Remplacer tgt par src
                elif os.path.isfile(tgtObj):
                    self.lCtrl.Add(relPath=relpathObj, action=_REMPLACEMENT, extension="folder", size=get_size(srcObj))
                # tgt répertoire: R�cursif
                elif os.path.isdir(tgtObj):
                    self.analyze(srcObj, tgtObj)
                # tgt de type inconnu
                else:
                    print "Cible de type inconnu: %s" % tgtObj
            # src de type inconnu
            else:
                print "Source de type inconnu: %s" % srcObj
        
        # Analyser la cible
        for obj in os.listdir(tgt):
            # Stop
            if self.stop == True:
                return
            
            srcObj = os.path.join(src, obj)
            tgtObj = os.path.join(tgt, obj)
            relpathObj = os.path.relpath(srcObj, self.tCtrl_src.GetValue())
             
            # src inexistant
            if not os.path.exists(srcObj):
                self.lCtrl.Add(relPath=relpathObj, action=_SUPPRESSION, extension=get_extension(tgtObj), size=get_size(tgtObj))
    
    
    
    def OnRun_run(self):
        '''
        @brief Mise à jour des répertoires.
        @details V�rifier les param�tres avant de lancer le thread de mise à jour.
        '''
        
        # Tests:
        # - aucune action en cours
        if self.thread_analyze is not None:
            return
        if self.thread_maj is not None:
            return
        # - champs corrects
        if not os.path.isdir(self.tCtrl_src.GetValue()):
            wx.MessageDialog(self, "Répertoire source incorrect", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        if not os.path.isdir(self.tCtrl_tgt.GetValue()):
            wx.MessageDialog(self, "Répertoire cible incorrect", "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
            return
        
        # D�sactiver les boutons
        self.button_analyze.Show(False)
        self.button_stop.Show(True)
        self.button_run.Enable(False)
        # D�sactiver les menus
        self.menuBar_action_analyze.Enable(False)
        self.menuBar_action_run.Enable(False)
        self.menuBar_action_stop.Enable(True)
        
        # Lancer le thread
        self.thread_maj = threading.Thread(target=self.OnThread_run, name="Mise à jour des fichiers")
        self.thread_maj.start()
        # self.OnThread_run()
    
    
    
    def OnThread_run(self):
        '''
        @brief Thread de mise à jour des répertoires.
        '''
        
        try:
            # Faire l'analyse
            if self.lCtrl.GetItemCount() == 0:
                src = self.tCtrl_src.GetValue()
                tgt = self.tCtrl_tgt.GetValue()
                self.analyze(src, tgt)
            
            # Barre de chargement
            self.chargement.SetRange(self.lCtrl.GetItemCount())
            self.chargement.SetValue(0)
            
            # Faire la mise à jour
            self.mise_a_jour_repertoires()
            
            self.lCtrl.DeleteAllItems()
            
            if not self.stop:
                self.chargement.SetValue(0)
                wx.MessageDialog(self, "Mise a jour termin�e", "Mise à jour", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
        except Exception, err:
            wx.MessageDialog(self, str(err), "Erreur", wx.OK | wx.ICON_EXCLAMATION).ShowModal()
        
        # Activer les boutons
        self.button_analyze.Show(True)
        self.button_stop.Show(False)
        self.button_run.Enable(True)
        self.bSizer_actions.Layout()
        # Activer les menus
        self.menuBar_action_analyze.Enable(True)
        self.menuBar_action_run.Enable(True)
        self.menuBar_action_stop.Enable(False)
        
        self.stop = False
        self.thread_maj = None
    
    def mise_a_jour_repertoires(self):
        '''
        @brief Mise à jour des répertoires.
        '''
        
        basePath_src = self.tCtrl_src.GetValue()
        basePath_tgt = self.tCtrl_tgt.GetValue()
        
        nb = self.lCtrl.GetItemCount()
        for ligne in xrange(nb):
            # Stop
            if self.stop == True:
                return
            
            action = self.lCtrl.GetAction(ligne)
            relpathObj = self.lCtrl.GetPath(ligne)
            srcObj = os.path.join(basePath_src, relpathObj)
            tgtObj = os.path.join(basePath_tgt, relpathObj)
            
            if action in [ _AJOUT, _MISEAJOUR, _REMPLACEMENT ]:
                try:
                    copy(srcObj, tgtObj)
                except Exception, err:
                    print str(err)
            elif action == _SUPPRESSION:
                try:
                    rm(tgtObj)
                except Exception, err:
                    print str(err)
            
            self.chargement.SetValue(self.chargement.GetValue() + 1)


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
        wx.Frame.__init__ (self, parent=parent, title="Préférences", size=sizeFenetre)
        self.SetSizeHints(minW=sizeFenetre.GetWidth(), minH=sizeFenetre.GetHeight(), maxW=sizeFenetre.GetWidth(), maxH=sizeFenetre.GetHeight())
        
        #     Sizer de la fenêtre
        self.sizer_frame = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(sizer=self.sizer_frame)
        
        #         Panel g�n�ral
        self.panel_fenetre = wx.Panel(parent=self)
        self.sizer_frame.Add(item=self.panel_fenetre, proportion=1, flag=wx.EXPAND, border=5)
        
        #             Sizer du panel g�n�ral
        self.sizer_panel = wx.BoxSizer(orient=wx.VERTICAL)
        self.panel_fenetre.SetSizer(sizer=self.sizer_panel)
        
        #                 Titre fenêtre
        sText_titre = wx.StaticText(parent=self.panel_fenetre, label="Param�tres")
        font_titre = wx.Font(pointSize=10, family=wx.FONTFAMILY_DEFAULT, style=wx.NORMAL, weight=wx.FONTWEIGHT_BOLD)
        sText_titre.SetFont(font=font_titre)
        self.sizer_panel.Add(item=sText_titre, flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border=5)
        
        #                 Ligne séparatrice
        ligne_titre_options = wx.StaticLine(parent=self.panel_fenetre)
        self.sizer_panel.Add(item=ligne_titre_options, flag=wx.ALL | wx.EXPAND, border=5)
        
        #                     Demande de confirmation de suppression
        self.cBox_confirmationSuppression = wx.CheckBox(parent=self.panel_fenetre, label=" Demande de confirmation de suppression")
        self.cBox_confirmationSuppression.SetValue(self.confirmationSuppression)
        self.cBox_confirmationSuppression.Bind(event=wx.EVT_CHECKBOX, handler=self.OnCheckBox_confirmationSuppression)
        self.sizer_panel.Add(item=self.cBox_confirmationSuppression, flag=wx.ALL, border=5)
        #                     Supprimer cible si la source n'existe pas
        self.cBox_supprimerCible = wx.CheckBox(parent=self.panel_fenetre, label=" Supprimer la cible si la source n'existe pas")
        self.cBox_supprimerCible.SetValue(self.supprimerCible)
        self.cBox_supprimerCible.Bind(event=wx.EVT_CHECKBOX, handler=self.OnCheckBox_supprimerCible)
        self.sizer_panel.Add(item=self.cBox_supprimerCible, flag=wx.ALL, border=5)
        #                     Ignorer les cibles plus r�centes
        self.cBox_ignorerCiblePlusRecente = wx.CheckBox(parent=self.panel_fenetre, label=" Ignorer les cibles plus r�centes que les sources")
        self.cBox_ignorerCiblePlusRecente.SetValue(self.ignorerCiblePlusRecente)
        self.cBox_ignorerCiblePlusRecente.Bind(event=wx.EVT_CHECKBOX, handler=self.OnCheckBox_ignorerCiblePlusRecente)
        self.sizer_panel.Add(item=self.cBox_ignorerCiblePlusRecente, flag=wx.ALL, border=5)
        
        # Événements
        self.Bind(event=wx.EVT_CLOSE, handler=self.OnClose)
    
    
    
    def OnClose(self, event):
        '''
        @brief Fermeture de la fenêtre.
        
        @param event: The event.
        '''
        
        self.Hide()
    
    
    
    ####################################################################################################
    # Événements: modification des param�tres
    ####################################################################################################
    
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
