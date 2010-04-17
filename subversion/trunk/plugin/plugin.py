'''
Created on 27.2.2010

@author: Peterko
'''


from subprocess import Popen, PIPE
from imports.etree import etree

import os

class Plugin(object):
    '''
    classdocs
    '''
    
    description = 'SVN'
    
    ID = 'svn-plugin-for-team'
    
    executable = 'svn'
    
    supported = ['checkin', 'diff', 'log', 'update', 'revert', 'resolve']
    
    
    def __init__(self, interface):
        '''
        Constructor
        '''
        # load interface
        self.interface = interface
        
        self.pluginAdapter = self.interface.GetAdapter()
        self.pluginGuiManager = self.pluginAdapter.GetGuiManager()
        
        
        self.pluginAdapter.AddNotification('team-project-opened', self.TeamProjectOpened)
        self.pluginAdapter.AddNotification('team-register-for-checkout', self.SendRegistrationForCheckout)
        self.pluginAdapter.AddNotification('team-checkout', self.Checkout)
        
        
        
        self.pluginAdapter.AddNotification('team-get-supported', self.GetSupported)
        
        self.SendRegistrationForCheckout()
        
        self.__fileName = None
        self.checkinMessage = None
    
    def SendRegistrationForCheckout(self):
        self.pluginAdapter.Notify('team-send-register-implementation-for-checkout', self.ID, self.description)
    
    def __AddAllNotifications(self):
        # zaregistruj si vsetky callbacky
        self.pluginAdapter.AddNotification('team-get-file-data', self.GetFileData)
        self.pluginAdapter.AddNotification('team-update', self.SvnUpdate)
        self.pluginAdapter.AddNotification('team-make-compatible', self.MakeCompatible)
        self.pluginAdapter.AddNotification('team-resolve', self.Resolve)
        self.pluginAdapter.AddNotification('team-checkin', self.Checkin)
        self.pluginAdapter.AddNotification('team-continue-checkin', self.ContinueCheckin)
        self.pluginAdapter.AddNotification('team-revert', self.Revert)
        self.pluginAdapter.AddNotification('team-get-log', self.Log)
        
        self.pluginAdapter.AddNotification('team-solve-conflicts-in-opened-project', self.SolveConflicts)
        
    def __RemoveAllNotifications(self):
        self.pluginAdapter.RemoveNotification('team-get-file-data', self.GetFileData)
        self.pluginAdapter.RemoveNotification('team-update', self.SvnUpdate)
        self.pluginAdapter.RemoveNotification('team-make-compatible', self.MakeCompatible)
        self.pluginAdapter.RemoveNotification('team-resolve', self.Resolve)
        self.pluginAdapter.RemoveNotification('team-checkin', self.Checkin)
        self.pluginAdapter.RemoveNotification('team-continue-checkin', self.ContinueCheckin)
        self.pluginAdapter.RemoveNotification('team-revert', self.Revert)
        self.pluginAdapter.RemoveNotification('team-get-log', self.Log)
        self.pluginAdapter.RemoveNotification('team-solve-conflicts-in-opened-project', self.SolveConflicts)
        
    def TeamProjectOpened(self, fileName):
        
        self.__fileName = fileName
        
        
        try:
            self.__RemoveAllNotifications()
        except Exception, e:
            pass
      
        if self.IsProjectVersioned():
            # pridaj si vsetky callbacky
            self.__AddAllNotifications()
            
            if not self.IsCompatible():
                
                self.pluginAdapter.Notify('team-ask-compatible')
            else:
                self.GetSupported()
                if self.IsInConflict():
                    
                    self.pluginAdapter.Notify('team-solve-conflicts', self.GetConflictingFiles(), self.__fileName)
        
            
    
    def GetSupported(self):
        if self.IsCompatible() and self.IsProjectVersioned():
            self.pluginAdapter.Notify('team-send-supported', self.supported)
    
        
    def GetFileData(self, idData, actionId, revision=None):
        if revision is None:
            rev = 'BASE'
        else:
            rev = revision
        command = [self.executable, 'cat', self.__fileName, '-r', rev]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        
        if p.returncode == 0:
            self.pluginAdapter.Notify('team-send-file-data', out, idData)
            self.pluginAdapter.Notify('team-continue-'+actionId)
        else:
            self.pluginAdapter.Notify('team-exception', err)
        
    # zisti, ci je projekt pod tymto verzovacim systemom    
    def IsProjectVersioned(self):
        
        command = [self.executable, 'status', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        return p.communicate()[1] == ''
        
     
   
    
        
    def SvnUpdate(self, revision=None):
        '''
        Run update, return new status of updated file
        '''
        print 'trying svn update to revision', revision
        if revision is None:
            rev = 'HEAD'
        else:
            rev = revision
        
        # run update    
        command = [self.executable, 'update', self.__fileName, '-r', rev, '--non-interactive']
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (result, err) = p.communicate()
        
        if self.IsInConflict():
            # treba reloadnut a riesit konflikty
            
            self.pluginAdapter.Notify('team-load-project', self.__fileName)
        
        else:
            # neboli lokalne zmeny a sam to prevalil
            
            self.pluginAdapter.Notify('team-send-result', result)
            self.pluginAdapter.Notify('team-load-project', self.__fileName)
    
    
    def IsCompatible(self):
        command = [self.executable, 'propget', 'svn:mime-type', self.__fileName, '--xml']
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        result = False
        if p.returncode == 0:
            r = etree.XML(out)
            
            for t in r:
                if t.tag == 'target':
                    if os.path.normpath(t.get('path')) == os.path.normpath(self.__fileName):
                        for p in t:
                            if p.tag == 'property':
                                if p.get('name') == 'svn:mime-type':
                                    if p.text == 'application/octet-stream':
                                        result = True
        return result
    
    def MakeCompatible(self):
        command = [self.executable, 'propset', 'svn:mime-type', 'application/octet-stream', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
    
    def IsInConflict(self):
        command2 = [self.executable, 'status', self.__fileName, '--xml']
        p2 = Popen(command2, stdout=PIPE, stderr=PIPE)
        (out, err2) = p2.communicate()
        
        
        r = etree.XML(out)
        wcStatus = r.find('.//wc-status')
        
        if wcStatus is not None:
            
            if wcStatus.get('item') == 'conflicted':
                return True
            
        return False
    
    def GetConflictingFiles(self):
        if self.IsInConflict():
            command3 = [self.executable, 'info', self.__fileName, '--xml']
            p3 = Popen(command3, stdout=PIPE, stderr=PIPE)
            (out, err2) = p3.communicate()
            r = etree.XML(out)
            baseFileName = r.find('.//prev-base-file').text
            newFileName = r.find('.//cur-base-file').text
             
            baseFile = os.path.join(os.path.dirname(self.__fileName), baseFileName)
            newFile = os.path.join(os.path.dirname(self.__fileName), newFileName)
            result = {'mine':self.__fileName, 'base':baseFile, 'new':newFile}
            print result 
            return result
        else:
            return None
            
    
    def Resolve(self):
        
        command = [self.executable, 'resolved', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (result, err) = p.communicate()
        print result, err
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
    
    def SolveConflicts(self):
        if self.IsInConflict():
            self.pluginAdapter.Notify('team-solve-conflicts', self.GetConflictingFiles(), self.__fileName)
        else:
            self.pluginAdapter.Notify('team-send-result', 'Project is not in conflict')
    
    
    
    def Checkin(self, message, username=None, password=None):
        if message is None:
            self.pluginAdapter.Notify('team-exception', 'Message is None')
        
        else:
            self.checkinMessage = message
            if username is None or password is None:
                command = [self.executable, 'commit', self.__fileName, '-m', message, '--non-interactive']
            else :
                command = [self.executable, 'commit', self.__fileName, '-m', message, '--non-interactive', '--username',username, '--password', password]
            p = Popen(command, stdout=PIPE, stderr=PIPE)
            (out, err) = p.communicate()
            if p.returncode == 0:
                self.pluginAdapter.Notify('team-send-result', out)
                self.checkinMessage = None
            else:
                if err.lower().find('authorization') != -1:
                    self.pluginAdapter.Notify('get-authorization', 'checkin')
                else:
                    # inak vrat chybovu hlasku
                    self.pluginAdapter.Notify('team-exception', err)
        
    def ContinueCheckin(self, username, password):
        self.Checkin(self.checkinMessage, username, password)
        
    def Revert(self):
        print 'trying svn revert'
        command = [self.executable, 'revert', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        p.communicate()
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
        self.pluginAdapter.Notify('team-send-result', 'Reverted')
        
    
    
    def Log(self):
        print 'trying svn log'
        command = [self.executable, 'log', self.__fileName, '--xml']
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        # out ma teraz xml
        root = etree.XML(out)
        result = []
        for e in root:
            d = {}
            d['revision'] = e.get('revision')
            for sub in e:
                if sub.tag == 'author':
                    d['author'] = sub.text
                elif sub.tag == 'date':
                    d['date'] = sub.text
                elif sub.tag == 'msg':
                    d['message'] = sub.text
            result.append(d)
        
        self.pluginAdapter.Notify('team-send-log', result)
        
    def Checkout(self, implId, url, directory, revision = None):
        print implId, self.ID
        if implId == self.ID:
            print 'trying svn checkout'
            if revision is None:
                rev = 'HEAD'
            else:
                rev = revision
            command = [self.executable, 'checkout', url, directory, '-r', rev]
            p = Popen(command, stdout=PIPE, stderr=PIPE)
            (out, err) = p.communicate()
            print 'out',out
            print 'err',err
            if err == '':
                self.pluginAdapter.Notify('team-send-result', out)
            else:
                self.pluginAdapter.Notify('team-exception', err)
    
    
# select plugin main object
pluginMain = Plugin