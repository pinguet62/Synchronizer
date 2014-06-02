#!/usr/bin/python
# -*- coding: utf-8 -*-



# Modules Python
import os
import time
import shutil
import threading
import win32com.shell.shell
import win32com.shell.shellcon
import win32con
import win32gui
import win32clipboard
import wx



def get_size( path ) :
    '''
    @brief Obtenir la taille de la cible.
    
    @patam path Chemin de la cible
    
    @return Taille en octet
    '''
    
    if os.path.isdir( path ) :
        size = 0
        for root, dirs, files in os.walk( path ) :
            for fich in files :
                size += os.path.getsize( os.path.join( root, fich ) )
    else :
        size = os.path.getsize( path )
    
    return size



def octetToHumainSize( size ) :
    '''
    @brief Convertir la taille en octet vers une mesure compréhensible par l'humain.
    
    @param size Taille en octet
    
    @return String représentant la taille (1 décimales près)
    '''
    
    if size == "" :
        return ""
    
    # o
    if size < 1024**1 :
        return "%do" % size
    # ko
    elif size < 1048576 :
        return "%.1fko" % (size/1024)
    # Mo
    elif size < 1073741824 :
        return "%.1fMo" % (size/1048576)
    # Go
    elif size < 1099511627776 :
        return "%.1fGo" % (size/1073741824)
    # To
    else :
        return "%.1fTo" % (size/1099511627776)



def get_extension( path ) :
    '''
    @brief Obtenir le type de la cible.
    
    @param path Chemin de la cible
    
    @return Son extension s'il s'agit d'un fichier, "folder" s'il s'agit d'un répertoire
    '''
    
    if os.path.isdir( path ) :
        return "folder"
    elif os.path.isfile( path ) :
        return os.path.splitext( path )[1].lower()
    else :
        return ""



def extension_to_bitmap( extension ) :
    '''
    @brief Obtenir l'image correspondante à l'extension.
    
    @param extension Extension
    
    @return Image correspondante
    '''
    
    # Type répertoire
    if extension == "folder" :
        bm = wx.Bitmap( name = "icones/folder.png", type = wx.BITMAP_TYPE_PNG )
        bm.SetSize( (16,16) )
        return bm
    
    
    flags = win32com.shell.shellcon.SHGFI_SMALLICON | win32com.shell.shellcon.SHGFI_ICON | win32com.shell.shellcon.SHGFI_USEFILEATTRIBUTES
    
    retval, info = win32com.shell.shell.SHGetFileInfo( extension,
                                                       win32con.FILE_ATTRIBUTE_NORMAL,
                                                       flags )
    
    assert retval
    
    hicon, iicon, attr, display_name, type_name = info
    
    icon = wx.EmptyIcon()
    icon.SetHandle( hicon )
    return wx.BitmapFromIcon( icon )



def copy( src, tgt ) :
    '''
    @brief Copier de fichier ou répertoire.
    
    @param src Chemin de la source
    @param tgt Chemin de la cible
    '''
    
    # Supprimer la cible existante
    if os.path.exists( tgt ) :
        rm( tgt )
    
    # Copier
    if os.path.isdir( src ) :
        shutil.copytree( src, tgt )
    else :
        shutil.copy2( src, tgt )



def rm( path ) :
    '''
    @brief Supprimer la cible.
    
    @param Chemin du fichier ou du répertoire
    '''
    
    if os.path.isdir( path ) :
        shutil.rmtree( path )
    else :
        os.remove( path )
    
    # Vérifications
    if os.path.exists( path ) :
        raise Exception( "Echec de la suppression" )



# Action sur les fichiers
_AJOUT = "ajout"               # Ajouter au répertoire cible
_MISEAJOUR = "mise a jour"     # Mettre à jour la cible
_REMPLACEMENT = "remplacement" # Remplacer le répertoire cible par le fichier source, ou remplacer le fichier cible par le répertoire source
_SUPPRESSION = "suppression"   # Supprimer la cible



class MyListCtrl( wx.ListCtrl ) :
    '''
    @class MyListCtrl
    @brief Redéfinition de la classe ListCtrl.
    @details Complète la classe ListCtrl en lui ajoutant des méthodes utiles à l'application.
    @author Pinguet
    @version 1
    '''
    
    
    
    # Colonnes
    _PATH = 0
    _EXTENSION = 1
    _ACTION = 2
    _TAILLE = 3
    
    
    
    def __init__( self, parent ) :
        '''
        @brief Constructeur.
        
        @param parent Objet parent
        '''
        
        self.basePath_src = None
        self.basePath_tgt = None
        
        # Constructeurs parents
        wx.ListCtrl.__init__( self, parent = parent, style = wx.LC_REPORT )
        
        # Noms de colonne
        self.InsertColumn( col = MyListCtrl._PATH, heading = "Path", width = 200 )
        self.InsertColumn( col = MyListCtrl._EXTENSION, heading = "Extension", width = 65 )
        self.InsertColumn( col = MyListCtrl._ACTION, heading = "Action", width = 89 )
        self.InsertColumn( col = MyListCtrl._TAILLE, heading = "Taille", width = 60 )
        
        # Icones
        self.listeImages = wx.ImageList( width = 16, height = 16 )
        self.extension_indiceImage = {} # Dictionnaire : extension du fichier -> indice de l'image
        
        # Evénements
        self.Bind( event = wx.EVT_LIST_ITEM_RIGHT_CLICK, handler = self.OnListItemRightClick )
        self.Bind( event = wx.EVT_LIST_KEY_DOWN, handler = self.OnListKeyDown )
    
    
    
    ####################################################################################################
    # Divers
    ####################################################################################################
    
    def SetBasePath( self, src = None, tgt = None ) :
        '''
        @param Définir le répertoire de base.
        
        @param src Répertoire source de base
        @param tgt Répertoire cible de base
        
        @exception ValueError Répertoire inexistant
        '''
        
        if src is not None :
            self.basePath_src = src
        if tgt is not None :
            self.basePath_tgt = tgt
    
    
    
    def GetIndiceImage( self, extension = "" ) :
        '''
        @brief Obtenir l'indice de l'image à partir de son extension.
        
        @param extension Extension
        
        @return Indice de l'image dans la liste
        '''
        
        # Extension connue
        if extension in self.extension_indiceImage :
            return self.extension_indiceImage[ extension ]
        
        # Nouvelle extension
        # - ajouter la nouvelle image à la ListCtrl
        bmp = extension_to_bitmap( extension )
        indice = self.listeImages.Add( bmp )
        self.SetImageList( self.listeImages, wx.IMAGE_LIST_SMALL )
        # - ajouter l'extension au dictionnaire
        self.extension_indiceImage[ extension ] = indice
        return indice
    
    
    
    ####################################################################################################
    # Modification des lignes
    ####################################################################################################
    
    def DeleteSelectedIndex( self ) :
        '''
        @brief Supprimer les lignes sélectionnées.
        '''
        
        ligne = self.GetFirstSelected()
        while ligne != -1 :
            self.DeleteItem( item = ligne )
            ligne = self.GetFirstSelected()
    
    
    
    def Add( self, relPath = "", extension = "", action = "", size = "" ) :
        '''
        @brief Ajouter une ligne dans la liste.
        
        @param relPath Chemin relatif du fichier ou répertoire
        @param extension Extension du fichier, vide si inconnu, ou "folder" pour un répertoire
        @param action Type de modification
        @param size Taille
        '''
        
        num = self.GetItemCount()
        
        # Image + Path
        indiceImage = self.GetIndiceImage( extension )
        self.InsertStringItem( index = num, label = relPath, imageIndex = indiceImage )
        
        # Extension
        if extension == "folder" :
            self.SetStringItem( index = num, col = MyListCtrl._EXTENSION, label = "" )
        else :
            self.SetStringItem( index = num, col = MyListCtrl._EXTENSION, label = extension )
        
        # Modification
        self.SetStringItem( index = num, col = MyListCtrl._ACTION, label = action )
        
        # Taille
        self.SetStringItem( index = num, col = MyListCtrl._TAILLE, label = octetToHumainSize( size ) )
    
    
    
    ####################################################################################################
    # Evénements divers
    ####################################################################################################
    
    def OnListKeyDown( self, event ) :
        '''
        @brief Pression d'une touche.
        
        @param event Evénement
        '''
        
        touche = event.GetKeyCode()
        if touche == wx.WXK_DELETE :
            if self.GetTopLevelParent().thread_analyse is None and self.GetTopLevelParent().thread_maj is None :
                self.DeleteSelectedIndex()
        # elif touche in [ wx.WXK_NUMPAD_ENTER ] :
            # self.OpenSelectedLines()
    
    
    
    def OnListItemRightClick( self, event ) :
        '''
        @brief Clic droit sur une ligne.
        
        @param event Evénement
        '''
        
        ligne = event.GetIndex()
        relPath = self.GetPath( index = ligne )
        if self.basePath_src is None :
            srcObj = None
        else :
            srcObj = os.path.join( self.basePath_src, relPath )
        if self.basePath_tgt is None :
            tgtObj = None
        else :
            tgtObj = os.path.join( self.basePath_tgt, relPath )
        
        menu = wx.Menu()
        
        # Supprimer la ligne
        mItem_supLine = wx.MenuItem( parentMenu = menu, id = wx.ID_ANY, text = "Supprimer la ligne" )
        self.Bind( event = wx.EVT_MENU,
                   handler = lambda( event ) :
                                 self.DeleteItem( item = ligne ),
                   source = mItem_supLine )
        menu.AppendItem( item = mItem_supLine )
        
        # Menu de la source
        if srcObj is not None and os.path.exists( srcObj ) :
            # - séparateur
            menu.AppendSeparator()
            # - aller à la source
            mItem_goSrc = wx.MenuItem( parentMenu = menu, id = wx.ID_ANY, text = "Ouvrir l'emplacement de la source" )
            self.Bind( event = wx.EVT_MENU,
                       handler = lambda( event ) :
                                     self.AllerA( os.path.dirname( srcObj ) ),
                       source = mItem_goSrc )
            menu.AppendItem( item = mItem_goSrc )
            # - supprimer la cible
            mItem_supSrc = wx.MenuItem( parentMenu = menu, id = wx.ID_ANY, text = "Supprimer la source" )
            self.Bind( event = wx.EVT_MENU,
                       handler = lambda( event ) :
                                     self.SupprimerSrc( relPath = relPath, index = ligne ),
                       source = mItem_supSrc )
            menu.AppendItem( item = mItem_supSrc )
        
        # Menu de la cible
        if tgtObj is not None and os.path.exists( tgtObj ) :
            # - séparateur
            menu.AppendSeparator()
            # - supprimer la cible
            mItem_goTgt = wx.MenuItem( parentMenu = menu, id = wx.ID_ANY, text = "Ouvrir l'emplacement de la cible" )
            self.Bind( event = wx.EVT_MENU,
                       handler = lambda( event ) :
                                     self.AllerA( os.path.dirname( tgtObj ) ),
                       source = mItem_goTgt )
            menu.AppendItem( item = mItem_goTgt )
            # - aller à la cible
            mItem_supTgt = wx.MenuItem( parentMenu = menu, id = wx.ID_ANY, text = "Supprimer la cible" )
            self.Bind( event = wx.EVT_MENU,
                       handler = lambda( event ) :
                                     self.SupprimerTgt( relPath = relPath, index = ligne ),
                       source = mItem_supTgt )
            menu.AppendItem( item = mItem_supTgt )
        
        self.PopupMenu( menu = menu )
    
    
    
    ####################################################################################################
    # Actions du menu
    ####################################################################################################
    
    def AllerA( self, path ) :
        '''
        @brief Ouvrir une fenêtre d'exploration Windows dans le répertoire spécifié.
        
        @param path Chemin du répertoire
        '''
        
        try :
            # Tests
            # - cible existante
            if not os.path.exists( path ) :
                raise ValueError( "Répertoire inexistant" )
            # - répertoire correct
            if not os.path.isdir( path ) :
                raise ValueError( "Cible incorrecte" )
            
            cmd = 'explorer "%s"' % path
            os.system( cmd )
        except Exception, err :
            wx.MessageDialog( parent = self, message = str( err ), caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
    
    
    
    def SupprimerSrc( self, relPath, index ) :
        '''
        @brief Supprimer le fichier ou répertoire source spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire source à supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join( self.basePath_src, relPath )
        tgtObj = os.path.join( self.basePath_tgt, relPath )
        
        try :
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression :
                mDialog = wx.MessageDialog( parent = self, message = "Voulez-vous vraiment supprimer la source ?", caption = "Supprimer source", style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION )
                if mDialog.ShowModal() == wx.ID_NO :
                    return
            # Supprimer la source
            rm( srcObj )
            
            if not os.path.exists( tgtObj ) :
                # Supprimer la ligne
                self.DeleteItem( item = index )
            else :
                # Mettre à jour la ligne
                extension = get_extension( tgtObj )
                indiceImage = self.GetIndiceImage( extension )
                self.SetStringItem( index = index, col = MyListCtrl._PATH, label = relPath, imageId = indiceImage )
                if extension == "folder" :
                    self.SetStringItem( index = index, col = MyListCtrl._EXTENSION, label = "" )
                else :
                    self.SetStringItem( index = index, col = MyListCtrl._EXTENSION, label = extension )
                self.SetStringItem( index = index, col = MyListCtrl._ACTION, label = _SUPPRESSION )
        except Exception, err :
            wx.MessageDialog( parent = self, message = str( err ), caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
    
    
    
    def SupprimerTgt( self, relPath, index ) :
        '''
        @brief Supprimer le fichier ou répertoire cible spéficié.
        
        @param relPath Chemin relatif du fichier ou du répertoire cible à supprimer
        @param index Numéro de ligne
        '''
        
        srcObj = os.path.join( self.basePath_src, relPath )
        tgtObj = os.path.join( self.basePath_tgt, relPath )
        
        try :
            # Demande de confirmation
            if self.GetTopLevelParent().preferences.confirmationSuppression :
                mDialog = wx.MessageDialog( parent = self, message = "Voulez-vous vraiment supprimer la cible ?", caption = "Supprimer cible", style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION )
                if mDialog.ShowModal() == wx.ID_NO :
                    return
            # Supprimer la source
            rm( tgtObj )
            
            if not os.path.exists( srcObj ) :
                # Supprimer la ligne
                self.DeleteItem( item = index )
            else :
                # Mettre à jour la ligne
                extension = get_extension( srcObj )
                indiceImage = self.GetIndiceImage( extension )
                self.SetStringItem( index = index, col = MyListCtrl._PATH, label = relPath, imageId = indiceImage )
                self.SetStringItem( index = index, col = MyListCtrl._EXTENSION, label = extension )
                self.SetStringItem( index = index, col = MyListCtrl._ACTION, label = _AJOUT )
        except Exception, err :
            wx.MessageDialog( parent = self, message = str( err ), caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
    
    
    
    ####################################################################################################
    # Informations sur les lignes
    ####################################################################################################
    
    def GetPath( self, index ) :
        '''
        @brief Obtenir le chemin de la ligne.
        
        @param index Numéro de ligne
        
        @return Chemin
        '''
        
        path = self.GetItem( itemId = index, col = MyListCtrl._PATH ).GetText()
        # return str( path )
        return path
    
    
    
    def GetExtention( self, index ) :
        '''
        @brief Obtenir l'extension de la ligne.
        
        @param index Numéro de ligne
        
        @return Extension
        '''
        
        extension = self.GetItem( itemId = index, col = MyListCtrl._EXTENSION ).GetText()
        # return str( extension )
        return extension
    
    
    
    def GetAction( self, index ) :
        '''
        @brief Obtenir l'action à effectuer de la ligne.
        
        @param index Numéro de ligne
        
        @return Action
        '''
        
        action = self.GetItem( itemId = index, col = MyListCtrl._ACTION ).GetText()
        # return str( action )
        return action
    
    
    def GetSize( self, index ) :
        '''
        @brief Obtenir la taille de la ligne.
        
        @param index Numéro de ligne
        
        @return Taille
        '''
        
        taille = self.GetItem( itemId = index, col = MyListCtrl._TAILLE ).GetText()
        return taille





class MyFrame( wx.Frame ) :
    '''
    @class MyFrame
    @brief Fenêtre de l'interface graphique.
    @details Fenêtre dynamique qui hérite de la fenêtre statique pour lui ajouter un comportement dynamique.
    @author Pinguet
    @version 1
    '''
    
    
    
    def __init__( self ) :
        '''
        @brief Constructeur.
        '''
        
        # Attributs du programme
        self.stop = False
        self.thread_analyse = None
        self.thread_maj = None
        
        # Fenêtres
        #     Application
        wx.Frame.__init__ ( self, parent = None, title = "Synchonisation", size = (500,700) )
        self.SetMinSize( (300,500) )
        self.CenterOnScreen()
        #     Préférences
        self.preferences = Preferences( parent = self )
        
        # Barre de menu
        barreMenu = wx.MenuBar()
        self.SetMenuBar( menubar = barreMenu )
        #     Fichier
        barreMenu_fichier = wx.Menu()
        barreMenu.Append( menu = barreMenu_fichier, title = "&Fichier" )
        #         Quitter
        barreMenu_fichier_quitter = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_fichier, text = "&Quitter\tAlt-F4" )
        barreMenu_fichier_quitter.SetBitmap( wx.Bitmap( name = "icones/quiter.png", type = wx.BITMAP_TYPE_PNG ) )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_fichier_quitter, source = barreMenu_fichier_quitter )
        barreMenu_fichier.AppendItem( item = barreMenu_fichier_quitter )
        #     Action
        barreMenu_action = wx.Menu()
        barreMenu.Append( menu = barreMenu_action, title = "Action" )
        #         Analyse
        self.barreMenu_action_analyse = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_action, text = "Analyse" )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_action_analyse, source = self.barreMenu_action_analyse )
        barreMenu_action.AppendItem( item = self.barreMenu_action_analyse )
        #         Mise à jour
        self.barreMenu_action_miseAJour = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_action, text = "Mise à jour" )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_action_miseAJour, source = self.barreMenu_action_miseAJour )
        barreMenu_action.AppendItem( item = self.barreMenu_action_miseAJour )
        #         Stop
        self.barreMenu_action_stop = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_action, text = "Stop" )
        self.barreMenu_action_stop.Enable( False )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_action_stop, source = self.barreMenu_action_stop )
        barreMenu_action.AppendItem( item = self.barreMenu_action_stop )
        #     Outils
        barreMenu_outils = wx.Menu()
        barreMenu.Append( menu = barreMenu_outils, title = "&Outils" )
        #         Préférences
        barreMenu_outils_preference = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_outils, text = "Préférences" )
        barreMenu_outils_preference.SetBitmap( wx.Bitmap( name = "icones/preferences.png", type = wx.BITMAP_TYPE_PNG ) )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_outils_preferences, source = barreMenu_outils_preference )
        barreMenu_outils.AppendItem( item = barreMenu_outils_preference )
        #     Aide
        barreMenu_aide = wx.Menu()
        barreMenu.Append( menu = barreMenu_aide, title = "&?" )
        #         À propos
        barreMenu_aide_aPropos = wx.MenuItem( id = wx.ID_ANY, parentMenu = barreMenu_aide, text = "À propos" )
        self.Bind( event = wx.EVT_MENU, handler = self.OnMenuSelection_aide_aPropos, source = barreMenu_aide_aPropos )
        barreMenu_aide.AppendItem( item = barreMenu_aide_aPropos )
        
        #     Sizer de la fenêtre
        self.sizer_frame = wx.BoxSizer( orient = wx.VERTICAL )
        self.SetSizer( sizer = self.sizer_frame )
        
        #         Panel général
        self.panel_fenetre = wx.Panel( parent = self )
        self.sizer_frame.Add( item = self.panel_fenetre, proportion = 1, flag = wx.EXPAND, border = 5 )
        
        #             Sizer du panel général
        self.sizer_panel = wx.BoxSizer( orient = wx.VERTICAL )
        self.panel_fenetre.SetSizer( sizer = self.sizer_panel )
        
        #                 Barre d'outil
        self.tBar = wx.ToolBar( parent = self.panel_fenetre, style = wx.TB_FLAT )
        self.sizer_panel.Add( item = self.tBar, flag = wx.EXPAND )
        #                     Quitter
        tool_quitter = self.tBar.AddLabelTool( id = wx.ID_ANY, label = "Quitter", bitmap = wx.Bitmap( name = "icones/quiter.png", type = wx.BITMAP_TYPE_PNG ) )
        self.tBar.Bind( event = wx.EVT_TOOL, handler = self.OnEventTool_quitter, source = tool_quitter )
        # 
        self.tBar.AddSeparator()
        #                     Supprimer les lignes sélectionnées
        tool_suppLigne = self.tBar.AddLabelTool( id = wx.ID_ANY, label = "Supprimer les lignes sélectionnées", bitmap = wx.Bitmap( name = "icones/supprimer.png", type = wx.BITMAP_TYPE_PNG ) )
        self.tBar.Bind( event = wx.EVT_TOOL, handler = self.OnEventTool_suppLignes, source = tool_suppLigne )
        # 
        self.tBar.Realize()
        
        #                 Titre fenêtre
        sText_titre = wx.StaticText( parent = self.panel_fenetre, label = "Application qui poutre" )
        font_titre = wx.Font( pointSize = 10, family = wx.FONTFAMILY_DEFAULT, style = wx.NORMAL, weight = wx.FONTWEIGHT_BOLD )
        sText_titre.SetFont( font = font_titre )
        self.sizer_panel.Add( item = sText_titre, flag = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border = 5 )
        
        #                 Ligne séparatrice
        ligne_titre_options = wx.StaticLine( parent = self.panel_fenetre )
        self.sizer_panel.Add( item = ligne_titre_options, flag = wx.ALL | wx.EXPAND, border = 5 )
        
        #                 Titre options
        sText_options = wx.StaticText( parent = self.panel_fenetre, label = "Options :" )
        font_titre_options = wx.Font( pointSize = wx.NORMAL_FONT.GetPointSize(), family = wx.FONTFAMILY_DEFAULT, style = wx.NORMAL, weight = wx.FONTWEIGHT_BOLD )
        sText_options.SetFont( font = font_titre_options )
        self.sizer_panel.Add( item = sText_options, flag = wx.ALL, border = 5 )
        
        #                 Sizer options
        gSizer_options = wx.GridSizer( cols = 3 )
        self.sizer_panel.Add( item = gSizer_options, flag = wx.ALL | wx.EXPAND, border = 5 )
        #                     Titre source
        sText_src = wx.StaticText( parent = self.panel_fenetre, label = "Répertoire source :" )
        gSizer_options.Add( item = sText_src, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Texte source
        self.tCtrl_src = wx.TextCtrl( parent = self.panel_fenetre, style = wx.TE_READONLY )
        gSizer_options.Add( item = self.tCtrl_src, flag = wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Bouton parcourir source
        self.button_src = wx.Button( parent = self.panel_fenetre, label = "Parcourir" )
        self.button_src.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_parcourirSrc )
        gSizer_options.Add( item = self.button_src, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Titre cible
        sText_tgt = wx.StaticText( parent = self.panel_fenetre, label = "Répertoire cible :" )
        gSizer_options.Add( item = sText_tgt, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Texte source
        self.tCtrl_tgt = wx.TextCtrl( parent = self.panel_fenetre, style = wx.TE_READONLY )
        gSizer_options.Add( item = self.tCtrl_tgt, flag = wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Bouton parcourir cible
        self.button_tgt = wx.Button( parent = self.panel_fenetre, label = "Parcourir" )
        self.button_tgt.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_parcourirTgt )
        gSizer_options.Add( item = self.button_tgt, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        
        #                 Ligne séparatrice
        ligne_options_modifications = wx.StaticLine( parent = self.panel_fenetre )
        self.sizer_panel.Add( item = ligne_options_modifications, flag = wx.ALL | wx.EXPAND, border = 5 )
        
        #                 Titre modifications
        sText_modifications = wx.StaticText( parent = self.panel_fenetre, label = "Modifications :" )
        font_titre_modifications = wx.Font( pointSize = wx.NORMAL_FONT.GetPointSize(), family = wx.FONTFAMILY_DEFAULT, style = wx.NORMAL, weight = wx.FONTWEIGHT_BOLD )
        sText_modifications.SetFont( font = font_titre_modifications )
        self.sizer_panel.Add( item = sText_modifications, flag = wx.ALL, border = 5 )
        
        #                 Liste des modifications
        self.lCtrl = MyListCtrl( parent = self.panel_fenetre )
        self.sizer_panel.Add( item = self.lCtrl, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 5 )
        
        #                 Sizer boutons d'action sur la liste
        # bSizer_buttonsListe = wx.BoxSizer( orient = wx.HORIZONTAL )
        # self.sizer_panel.Add( item = bSizer_buttonsListe, flag = wx.ALL | wx.EXPAND, border = 5 )
        #                     Bouton "supprimer la ligne"
        # bm_supprimer = wx.Bitmap( name = "icones/supprimer.png", type = wx.BITMAP_TYPE_ANY )
        # bmButton_supprimer = wx.BitmapButton( self.panel_fenetre, bitmap = bm_supprimer, size = (20,20) )
        # bmButton_supprimer.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_supprimerSelection )
        # bSizer_buttonsListe.Add( item = bmButton_supprimer, flag = wx.ALL, border = 5 )
        
        #                 Ligne séparatrice
        ligne_modifications_actions = wx.StaticLine( parent = self.panel_fenetre )
        self.sizer_panel.Add( item = ligne_modifications_actions, flag = wx.ALL | wx.EXPAND, border = 5 )
        
        #                 Sizer actions
        self.bSizer_actions = wx.BoxSizer( orient = wx.HORIZONTAL )
        self.sizer_panel.Add( item = self.bSizer_actions, flag = wx.ALL | wx.EXPAND, border = 5 )
        #                     Bouton stop
        self.button_stop = wx.Button( parent = self.panel_fenetre, label = "Stop" )
        self.button_stop.Show( False )
        self.button_stop.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_stop )
        self.bSizer_actions.Add( item = self.button_stop, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Bouton analyse
        self.button_analyse = wx.Button( parent = self.panel_fenetre, label = "Analyse" )
        self.button_analyse.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_analyse )
        self.bSizer_actions.Add( item = self.button_analyse, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        #                     Barre de chargement
        self.chargement = wx.Gauge( parent = self.panel_fenetre )
        self.bSizer_actions.Add( item = self.chargement, proportion = 1, flag = wx.ALL, border = 5 )
        #                     Bouton mise à jour
        self.button_miseAJour = wx.Button( parent = self.panel_fenetre, label = "Mise à jour" )
        self.button_miseAJour.Bind( event = wx.EVT_BUTTON, handler = self.OnButtonClick_miseAJour )
        self.bSizer_actions.Add( item = self.button_miseAJour, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        
        # Bouton de test
        button_test = wx.Button( parent = self.panel_fenetre, label = "test" )
        button_test.Bind( event = wx.EVT_BUTTON, handler = self.test )
        self.bSizer_actions.Add( item = button_test, flag = wx.ALL | wx.ALIGN_CENTER_VERTICAL, border = 5 )
        
        # Evénements
        self.Bind( event = wx.EVT_CLOSE, handler = self.OnClose )
        
        
        self.init()
    
    
    
    def init( self ) :
        if os.path.exists( "..\\Cas_test" ) :
            shutil.rmtree( "..\\Cas_test" )
        shutil.copytree( "..\\Cas_test_sauv", "..\\Cas_test" )
        self.tCtrl_src.SetValue( "..\\Cas_test\\src" )
        self.tCtrl_tgt.SetValue( "..\\Cas_test\\tgt" )
        self.OnButtonClick_analyse( None )
        
    def test( self, event ) :
        print octetToHumainSize( 1023 )
        print octetToHumainSize( 1024 )
        print octetToHumainSize( 1025 )
        print octetToHumainSize( 2048 )
    
    
    
    ####################################################################################################
    # Evénements : divers
    ####################################################################################################
    
    def OnClose( self, event ) :
        '''
        @brief Fermeture de la fenêtre
        
        @param event Evémenement
        '''
        
        if self.preferences.confirmationQuitter :
            # Analyse en cours
            if self.thread_analyse is not None :
                mDialog = wx.MessageDialog( parent = self, message = "Analyse en cours. Êtes-vous sûr de vouloir quitter ?", caption = "Quitter", style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION )
                if mDialog.ShowModal() == wx.ID_NO :
                    return
            # Mise à jour en cours
            elif self.thread_maj is not None :
                mDialog = wx.MessageDialog( parent = self, message = "Mise à jour en cours. Êtes-vous sûr de vouloir quitter ?", caption = "Quitter", style = wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION )
                if mDialog.ShowModal() == wx.ID_NO :
                    return
        
        self.stop = True
        # while self.thread_analyse is not None :
            # pass
        # while self.thread_maj is not None :
            # pass
        
        self.preferences.Destroy()
        event.Skip()
    
    
    
    ####################################################################################################
    # Evénements : menu
    ####################################################################################################
    
    def OnMenuSelection_fichier_quitter( self, event ) :
        '''
        @brief Menu : Fichier > Quitter
        
        @param event Evénement
        '''
        
        self.Close()
    
    
    
    def OnMenuSelection_action_analyse( self, event ) :
        '''
        @brief Menu : Action > Analyse
        
        @param event Evénement
        '''
        
        self.OnRun_analyse()
    
    
    
    def OnMenuSelection_action_miseAJour( self, event ) :
        '''
        @brief Menu : Action > Mise à jour
        
        @param event Evénement
        '''
        
        self.OnRun_miseAJour()
    
    
    
    def OnMenuSelection_action_stop( self, event ) :
        '''
        @brief Menu : Action > Stop
        
        @param event Evénement
        '''
        
        self.stop = True
    
    
    
    def OnMenuSelection_outils_preferences( self, event ) :
        '''
        @brief Menu : Outils > Préférences
        
        @param event Evénement
        '''
        
        self.preferences.Show()
        event.Skip()
    
    
    
    def OnMenuSelection_aide_aPropos( self, event ) :
        '''
        @brief Menu : Aide > À propos
        
        @param event Evénement
        '''
        
        print "À propos"
    
    
    
    ####################################################################################################
    # Evénements : Barre d'outil
    ####################################################################################################
    
    def OnEventTool_quitter( self, event ) :
        '''
        @brief Barre d'outil : Quitter
        
        @param event Evénement
        '''
        
        self.Close()
    
    
    
    def OnEventTool_suppLignes( self, event ) :
        '''
        @brief Barre d'outil : Supprimer les lignes sélectionnées
        
        @param event Evénement
        '''
        
        self.lCtrl.DeleteSelectedIndex()
    
    
    
    def OnEventTool_ajoutLignes( self, event ) :
        '''
        @brief Barre d'outil : Quitter
        
        @param event Evénement
        '''
        
        print "ajouter ligne"
    
    
    
    ####################################################################################################
    # Evénements : choix des répertoires
    ####################################################################################################
    
    def OnButtonClick_parcourirSrc( self, event ) :
        '''
        @brief Clic sur le button "Parcourir" la source.
        
        @param event Evémenement
        '''
        
        dDialog = wx.DirDialog( parent = self.panel_fenetre, message = "Répertoire source", style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST )
        # Vérifications :
        # - répertoire choisi
        if dDialog.ShowModal() != wx.ID_OK :
            return
        path = dDialog.GetPath()
        # - changement de cible
        if path == self.tCtrl_src.GetValue() :
            return
        # - source différente de la cible
        if path == self.tCtrl_tgt.GetValue() :
            self.tCtrl_tgt.SetValue( value = "" )
        
        self.tCtrl_src.SetValue( value = path )
        self.lCtrl.SetBasePath( src = self.tCtrl_src.GetValue(), tgt = self.tCtrl_tgt.GetValue() )
        self.lCtrl.DeleteAllItems()
    
    
    
    def OnButtonClick_parcourirTgt( self, event ) :
        '''
        @brief Clic sur le button "Parcourir" la cible.
        
        @param event Evémenement
        '''
        
        dDialog = wx.DirDialog( parent = self.panel_fenetre, message = "Répertoire source", style = wx.DD_DEFAULT_STYLE )
        # Vérifications :
        # - répertoire choisi
        if dDialog.ShowModal() != wx.ID_OK :
            return
        path = dDialog.GetPath()
        # - changement de cible
        if path == self.tCtrl_tgt.GetValue() :
            return
        # - cible différente de la source
        if path == self.tCtrl_src.GetValue() :
            wx.MessageDialog( parent = self, message = "Répertoire cible identique à la source", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        
        self.tCtrl_tgt.SetValue( value = path )
        self.lCtrl.SetBasePath( src = self.tCtrl_src.GetValue(), tgt = self.tCtrl_tgt.GetValue() )
        self.lCtrl.DeleteAllItems()
    
    
    
    ####################################################################################################
    # Evénements : barre d'outils
    ####################################################################################################
    
    def OnButtonClick_supprimerSelection( self, event ) :
        '''
        @brief Clic sur le bouton "supprimer".
        
        @param event Evénement
        '''
        
        self.lCtrl.DeleteSelectedIndex()
    
    
    
    ####################################################################################################
    # Evénements : boutons d'action
    ####################################################################################################
    
    def OnButtonClick_stop( self, event ) :
        '''
        @brief Clic sur le bouton "Stop"
        
        @param event Evémenement
        '''
        
        self.stop = True
    
    
    
    def OnButtonClick_analyse( self, event ) :
        '''
        @brief Clic sur le bouton "Analyser".
        
        @param event Evémenement
        '''
        
        self.OnRun_analyse()
    
    
    
    def OnButtonClick_miseAJour( self, event ) :
        '''
        @brief Clic sur le bouton "Mise à jour".
        
        @param event Evémenement
        '''
        
        self.OnRun_miseAJour()
    
    
    
    ####################################################################################################
    # Analyse et mise à jour des fichiers et répertoires
    ####################################################################################################
    
    def OnRun_analyse( self ) :
        '''
        @brief Analyse des répertoires.
        @details Vérifier les paramètres avant de lancer le thread l'analyse.
        '''
        
        # Tests :
        # - aucune action en cours
        if self.thread_analyse is not None :
            return
        if self.thread_maj is not None :
            return
        # - champs corrects
        if not os.path.isdir( self.tCtrl_src.GetValue() ) :
            wx.MessageDialog( parent = self, message = "Répertoire source incorrect", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        if not os.path.isdir( self.tCtrl_tgt.GetValue() ) :
            wx.MessageDialog( parent = self, message = "Répertoire cible incorrect", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        if self.tCtrl_src.GetValue() == self.tCtrl_tgt.GetValue() :
            wx.MessageDialog( parent = self, message = "Répertoire identiques", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        
        # Désactiver les boutons
        self.button_analyse.Show( False )
        self.button_stop.Show( True )
        self.button_miseAJour.Enable( False )
        # Désactiver les menus
        self.barreMenu_action_analyse.Enable( False )
        self.barreMenu_action_miseAJour.Enable( False )
        self.barreMenu_action_stop.Enable( True )
        
        # Lancer le thread
        self.thread_analyse = threading.Thread( target = self.OnThread_analyse, name = "Analyse des répertoires" )
        self.thread_analyse.start()
        # self.OnThread_analyse() # tmp
    
    
    
    def OnThread_analyse( self ) :
        '''
        @brief Thread d'analyse des répertoires.
        '''
        
        try :
            self.lCtrl.DeleteAllItems()
            
            # Faire l'analyse
            src = self.tCtrl_src.GetValue()
            tgt = self.tCtrl_tgt.GetValue()
            self.analyse( src, tgt )
        except Exception, err :
            wx.MessageDialog( parent = self, message = str( err ), caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
        
        # Activer les boutons
        self.button_analyse.Show( True )
        self.button_stop.Show( False )
        self.button_miseAJour.Enable( True )
        self.bSizer_actions.Layout()
        # Activer les menus
        self.barreMenu_action_analyse.Enable( True )
        self.barreMenu_action_miseAJour.Enable( True )
        self.barreMenu_action_stop.Enable( False )
        
        self.stop = False
        self.thread_analyse = None
    
    
    
    def analyse( self, src, tgt ) :
        '''
        @brief Comparaison et analyse des 2 cibles.
        @remark Fonction récursive.
        
        @param src Chemin absolu du répertoire source
        @param tgt Chemin absolu du répertoire cible
        '''
        
        # Analyser la source
        for obj in os.listdir( src ) :
            # Stop
            if self.stop == True :
                return
            
            srcObj = os.path.join( src, obj )
            tgtObj = os.path.join( tgt, obj )
            relpathObj = os.path.relpath( srcObj, self.tCtrl_src.GetValue() )
            
            # src = fichier
            if os.path.isfile( srcObj ) :
                # tgt inexistant : Copier
                if not os.path.exists( tgtObj ) :
                    self.lCtrl.Add( relPath = relpathObj, action = _AJOUT, extension = get_extension( srcObj ), size = get_size( srcObj ) )
                # tgt fichier : Comparer dates + remplacer
                elif os.path.isfile( tgtObj ) :
                    if os.path.getmtime( tgtObj ) + 0.0001 < os.path.getmtime( srcObj ) :
                        self.lCtrl.Add( relPath = relpathObj, action = _MISEAJOUR, extension = get_extension( srcObj ), size = get_size( srcObj ) )
                    if not self.preferences.ignorerCiblePlusRecente :
                        if os.path.getmtime( tgtObj ) > os.path.getmtime( srcObj ) + 0.0001 :
                            self.lCtrl.Add( relPath = relpathObj, action = _MISEAJOUR, extension = get_extension( srcObj ), size = get_size( srcObj ) )
                # tgt répertoire : Remplacer tgt par src
                elif os.path.isdir( tgtObj ) :
                    self.lCtrl.Add( relPath = relpathObj, action = _REMPLACEMENT, extension = get_extension( srcObj ), size = get_size( srcObj ) )
                # tgt de type inconnu
                else :
                    print "Cible de type inconnu : %s" % tgtObj
            # src = répertoire
            elif os.path.isdir( srcObj ) :
                # tgt inexistant : Copier
                if not os.path.exists( tgtObj ) :
                    self.lCtrl.Add( relPath = relpathObj, action = _AJOUT, extension = "folder", size = get_size( srcObj ) )
                # tgt fichier : Remplacer tgt par src
                elif os.path.isfile( tgtObj ) :
                    self.lCtrl.Add( relPath = relpathObj, action = _REMPLACEMENT, extension = "folder", size = get_size( srcObj ) )
                # tgt répertoire : Récursif
                elif os.path.isdir( tgtObj ) :
                    self.analyse( srcObj, tgtObj )
                # tgt de type inconnu
                else :
                    print "Cible de type inconnu : %s" % tgtObj
            # src de type inconnu
            else :
                print "Source de type inconnu : %s" % srcObj
        
        # Analyser la cible
        for obj in os.listdir( tgt ) :
            # Stop
            if self.stop == True :
                return
            
            srcObj = os.path.join( src, obj )
            tgtObj = os.path.join( tgt, obj )
            relpathObj = os.path.relpath( srcObj, self.tCtrl_src.GetValue() )
             
            # src inexistant
            if not os.path.exists( srcObj ) :
                self.lCtrl.Add( relPath = relpathObj, action = _SUPPRESSION, extension = get_extension( tgtObj ), size = get_size( tgtObj ) )
    
    
    
    def OnRun_miseAJour( self ) :
        '''
        @brief Mise à jour des répertoires.
        @details Vérifier les paramètres avant de lancer le thread de mise à jour.
        '''
        
        # Tests :
        # - aucune action en cours
        if self.thread_analyse is not None :
            return
        if self.thread_maj is not None :
            return
        # - champs corrects
        if not os.path.isdir( self.tCtrl_src.GetValue() ) :
            wx.MessageDialog( parent = self, message = "Répertoire source incorrect", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        if not os.path.isdir( self.tCtrl_tgt.GetValue() ) :
            wx.MessageDialog( parent = self, message = "Répertoire cible incorrect", caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
            return
        
        # Désactiver les boutons
        self.button_analyse.Show( False )
        self.button_stop.Show( True )
        self.button_miseAJour.Enable( False )
        # Désactiver les menus
        self.barreMenu_action_analyse.Enable( False )
        self.barreMenu_action_miseAJour.Enable( False )
        self.barreMenu_action_stop.Enable( True )
        
        # Lancer le thread
        self.thread_maj = threading.Thread( target = self.OnThread_miseAJour, name = "Mise à jour des fichiers" )
        self.thread_maj.start()
        # self.OnThread_miseAJour()
    
    
    
    def OnThread_miseAJour( self ) :
        '''
        @brief Thread de mise à jour des répertoires.
        '''
        
        try :
            # Faire l'analyse
            if self.lCtrl.GetItemCount() == 0 :
                src = self.tCtrl_src.GetValue()
                tgt = self.tCtrl_tgt.GetValue()
                self.analyse( src, tgt )
            
            # Barre de chargement
            self.chargement.SetRange( self.lCtrl.GetItemCount() )
            self.chargement.SetValue( 0 )
            
            # Faire la mise à jour
            self.mise_a_jour_repertoires()
            
            self.lCtrl.DeleteAllItems()
            
            if not self.stop :
                self.chargement.SetValue( 0 )
                wx.MessageDialog( parent = self, message = "Mise a jour terminée", caption = "Mise à jour", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
        except Exception, err :
            wx.MessageDialog( parent = self, message = str( err ), caption = "Erreur", style = wx.OK | wx.ICON_EXCLAMATION ).ShowModal()
        
        # Activer les boutons
        self.button_analyse.Show( True )
        self.button_stop.Show( False )
        self.button_miseAJour.Enable( True )
        self.bSizer_actions.Layout()
        # Activer les menus
        self.barreMenu_action_analyse.Enable( True )
        self.barreMenu_action_miseAJour.Enable( True )
        self.barreMenu_action_stop.Enable( False )
        
        self.stop = False
        self.thread_maj = None
    
    
    
    def mise_a_jour_repertoires( self ) :
        '''
        @brief Mise à jour des répertoires.
        '''
        
        basePath_src = self.tCtrl_src.GetValue()
        basePath_tgt = self.tCtrl_tgt.GetValue()
        
        nb = self.lCtrl.GetItemCount()
        for ligne in xrange( nb ) :
            # Stop
            if self.stop == True :
                return
            
            action = self.lCtrl.GetAction( ligne )
            relpathObj = self.lCtrl.GetPath( ligne )
            srcObj = os.path.join( basePath_src, relpathObj )
            tgtObj = os.path.join( basePath_tgt, relpathObj )
            
            if action in [ _AJOUT, _MISEAJOUR, _REMPLACEMENT ] :
                try :
                    copy( srcObj, tgtObj )
                except Exception, err :
                    print str( err )
            elif action == _SUPPRESSION :
                try :
                    rm( tgtObj )
                except Exception, err :
                    print str( err )
            
            self.chargement.SetValue( self.chargement.GetValue() + 1 )





class Preferences( wx.Frame ) :
    '''
    @class Preferences
    @brief Fenêtre des réglages de l'application.
    @author Pinguet
    @version 1
    '''
    
    
    
    def __init__( self, parent ) :
        '''
        @brief Constructeur.
        '''
        
        # Préférences du programme
        self.confirmationQuitter = True
        self.confirmationSuppression = True
        self.supprimerCible = True
        self.ignorerCiblePlusRecente = True
        
        # Fenêtre
        sizeFenetre = wx.Size( w = 275, h = 150 )
        wx.Frame.__init__ ( self, parent = parent, title = "Préférences", size = sizeFenetre )
        self.SetSizeHints( minW = sizeFenetre.GetWidth(), minH = sizeFenetre.GetHeight(), maxW = sizeFenetre.GetWidth(), maxH = sizeFenetre.GetHeight() )
        
        #     Sizer de la fenêtre
        self.sizer_frame = wx.BoxSizer( orient = wx.VERTICAL )
        self.SetSizer( sizer = self.sizer_frame )
        
        #         Panel général
        self.panel_fenetre = wx.Panel( parent = self )
        self.sizer_frame.Add( item = self.panel_fenetre, proportion = 1, flag = wx.EXPAND, border = 5 )
        
        #             Sizer du panel général
        self.sizer_panel = wx.BoxSizer( orient = wx.VERTICAL )
        self.panel_fenetre.SetSizer( sizer = self.sizer_panel )
        
        #                 Titre fenêtre
        sText_titre = wx.StaticText( parent = self.panel_fenetre, label = "Paramètres" )
        font_titre = wx.Font( pointSize = 10, family = wx.FONTFAMILY_DEFAULT, style = wx.NORMAL, weight = wx.FONTWEIGHT_BOLD )
        sText_titre.SetFont( font = font_titre )
        self.sizer_panel.Add( item = sText_titre, flag = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, border = 5 )
        
        #                 Ligne séparatrice
        ligne_titre_options = wx.StaticLine( parent = self.panel_fenetre )
        self.sizer_panel.Add( item = ligne_titre_options, flag = wx.ALL | wx.EXPAND, border = 5 )
        
        #                     Demande de confirmation de suppression
        self.cBox_confirmationSuppression = wx.CheckBox( parent = self.panel_fenetre, label = " Demande de confirmation de suppression" )
        self.cBox_confirmationSuppression.SetValue( self.confirmationSuppression )
        self.cBox_confirmationSuppression.Bind( event = wx.EVT_CHECKBOX, handler = self.OnCheckBox_confirmationSuppression )
        self.sizer_panel.Add( item = self.cBox_confirmationSuppression, flag = wx.ALL, border = 5 )
        #                     Supprimer cible si la source n'existe pas
        self.cBox_supprimerCible = wx.CheckBox( parent = self.panel_fenetre, label = " Supprimer la cible si la source n'existe pas" )
        self.cBox_supprimerCible.SetValue( self.supprimerCible )
        self.cBox_supprimerCible.Bind( event = wx.EVT_CHECKBOX, handler = self.OnCheckBox_supprimerCible )
        self.sizer_panel.Add( item = self.cBox_supprimerCible, flag = wx.ALL, border = 5 )
        #                     Ignorer les cibles plus récentes
        self.cBox_ignorerCiblePlusRecente = wx.CheckBox( parent = self.panel_fenetre, label = " Ignorer les cibles plus récentes que les sources" )
        self.cBox_ignorerCiblePlusRecente.SetValue( self.ignorerCiblePlusRecente )
        self.cBox_ignorerCiblePlusRecente.Bind( event = wx.EVT_CHECKBOX, handler = self.OnCheckBox_ignorerCiblePlusRecente )
        self.sizer_panel.Add( item = self.cBox_ignorerCiblePlusRecente, flag = wx.ALL, border = 5 )
        
        # Evénements
        self.Bind( event = wx.EVT_CLOSE, handler = self.OnClose )
    
    
    
    def OnClose( self, event ) :
        '''
        @brief Fermeture de la fenêtre.
        
        @param event Evémenement
        '''
        
        self.Hide()
    
    
    
    ####################################################################################################
    # Evénements : modification des paramètres
    ####################################################################################################
    
    def OnCheckBox_confirmationSuppression( self, event ) :
        '''
        @brief Clic sur la case "Demande de confirmation de suppression".
        
        @param event Evémenement
        '''
        
        self.confirmationSuppression = self.cBox_confirmationSuppression.IsChecked()
        event.Skip()
    
    
    
    def OnCheckBox_supprimerCible( self, event ) :
        '''
        @brief Clic sur la case "Supprimer la cible si la source n'existe pas".
        
        @param event Evémenement
        '''
        
        self.supprimerCible = self.cBox_supprimerCible.IsChecked()
        event.Skip()
    
    
    
    def OnCheckBox_ignorerCiblePlusRecente( self, event ) :
        '''
        @brief Clic sur la case " Ignorer les cibles plus récentes que les sources".
        
        @param event Evémenement
        '''
        
        self.ignorerCiblePlusRecente = self.cBox_ignorerCiblePlusRecente.IsChecked()
        event.Skip()








if __name__ == '__main__' :
    ex = wx.App( redirect = False )
    fen = MyFrame()
    fen.Show( True )
    # fen.CenterOnScreen()
    ex.MainLoop()