'''
Created on 27.2.2010

@author: Peterko
'''


from subprocess import Popen, PIPE
from imports.etree import etree

import os

class Plugin(object):
    '''
    Subversion plugin for Team
    '''
    
    description = 'SVN'
    
    ID = 'svn-plugin-for-team'
    
    executable = 'svn'
    
    supported = ['checkin', 'diff', 'log', 'update', 'revert', 'resolve']
    
    
    def __init__(self, interface):
        '''
        Constructor for Subversion plugin
        @type interface: CInterface
        @param interface: Plugin system interface  
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
        
    
    def SendRegistrationForCheckout(self):
        '''
        Register itself for checkout
        '''
        self.pluginAdapter.Notify('team-send-register-implementation-for-checkout', self.ID, self.description)
    
    def __AddAllNotifications(self):
        '''
        Register all notifications
        '''
        # zaregistruj si vsetky callbacky
        self.pluginAdapter.AddNotification('team-get-file-data', self.GetFileData)
        self.pluginAdapter.AddNotification('team-update', self.Update)
        self.pluginAdapter.AddNotification('team-make-compatible', self.MakeCompatible)
        self.pluginAdapter.AddNotification('team-resolve', self.Resolve)
        self.pluginAdapter.AddNotification('team-checkin', self.Checkin)
        self.pluginAdapter.AddNotification('team-revert', self.Revert)
        self.pluginAdapter.AddNotification('team-get-log', self.Log)
        self.pluginAdapter.AddNotification('team-solve-conflicts-in-opened-project', self.SolveConflicts)
        
    def __RemoveAllNotifications(self):
        '''
        Unregister all notifications
        '''
        self.pluginAdapter.RemoveNotification('team-get-file-data', self.GetFileData)
        self.pluginAdapter.RemoveNotification('team-update', self.Update)
        self.pluginAdapter.RemoveNotification('team-make-compatible', self.MakeCompatible)
        self.pluginAdapter.RemoveNotification('team-resolve', self.Resolve)
        self.pluginAdapter.RemoveNotification('team-checkin', self.Checkin)
        self.pluginAdapter.RemoveNotification('team-revert', self.Revert)
        self.pluginAdapter.RemoveNotification('team-get-log', self.Log)
        self.pluginAdapter.RemoveNotification('team-solve-conflicts-in-opened-project', self.SolveConflicts)
        
    def TeamProjectOpened(self, fileName):
        """
        Executes when project is opened. Should check if project is versioned with this VCS. 
        Should ask for compatibility and send team conflicts.
        @type fileName: string
        @param fileName: filename of project file
        """
        
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
        '''
        Hook executed when team plugin demands supported commands. Notify team plugin with supported commands
        '''
        if self.IsCompatible() and self.IsProjectVersioned():
            self.pluginAdapter.Notify('team-send-supported', self.supported)
    
        
    def GetFileData(self, username, password, trust, idData, actionId, revision=None):
        '''
        Hook executed when team plugin demands file data. Should notify team plugin back with data
        or with demand for authorization or with demand for server certification trusting or with 
        exception 
        @type username: string
        @param username: username
        @type password: string
        @param password: password
        @type trust: bool
        @param trust: True if server certificate has to be trusted
        @type idData: string
        @param idData: identification of demanded file data
        @type actionId: string
        @param actionId: identification of action that demanded file data
        @type revision: string
        @param revision: Revision of data
        '''
        if revision is None:
            rev = 'BASE'
        else:
            rev = revision
        command = [self.executable, 'cat', self.__fileName, '-r', rev, '--non-interactive']
        if username is not None and password is not None:
            command.extend(['--username',username,'--password',password])
            
        if trust:
            command.append('--trust-server-cert')
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        
        if p.returncode == 0:
            self.pluginAdapter.Notify('team-send-file-data', out, idData)
            self.pluginAdapter.Notify('team-continue-'+actionId)
        else:
            if err.lower().find('verification failed') != -1 and err.lower().find('different hostname')==-1:
                self.pluginAdapter.Notify('team-ask-server-cert', 'team-get-file-data', err, idData, actionId, revision)
            elif err.lower().find('authorization') != -1:
                self.pluginAdapter.Notify('team-get-authorization', 'team-get-file-data', trust, idData, actionId, revision)
            else:
                # inak vrat chybovu hlasku
                self.pluginAdapter.Notify('team-exception', err)
        
    # zisti, ci je projekt pod tymto verzovacim systemom    
    def IsProjectVersioned(self):
        '''
        Checks if project is version with this VCS
        @rtype: bool
        @return: True if project is version with this VCS, False otherwise
        '''
        command = [self.executable, 'status', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        return p.communicate()[1] == ''
        
     
   
    
        
    def Update(self, username=None, password=None, trust=False, revision=None):
        '''
        Hook executed when team plugin demands update. Should notify team plugin back with update result
        or with demand for authorization or with demand for server certification trusting or with 
        exception 
        @type username: string
        @param username: username
        @type password: string
        @param password: password
        @type trust: bool
        @param trust: True if server certificate has to be trusted
        @type revision: string
        @param revision: Revision of data
        '''
        if revision is None:
            rev = 'HEAD'
        else:
            rev = revision
        
        # run update  
          
        command = [self.executable, 'update', self.__fileName, '-r', rev, '--non-interactive']
        if username is not None and password is not None:
            command.extend(['--username' ,username, '--password' ,password])
            
        if trust:
            command.append('--trust-server-cert')
        
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (result, err) = p.communicate()
        
        if p.returncode == 0:
            
            if self.IsInConflict():
                # treba reloadnut a riesit konflikty
                
                self.pluginAdapter.Notify('team-load-project', self.__fileName)
            
            else:
                # neboli lokalne zmeny a sam to prevalil
                
                self.pluginAdapter.Notify('team-send-result', result)
                self.pluginAdapter.Notify('team-load-project', self.__fileName)
        else:
            
            if err.lower().find('verification failed') != -1 and err.lower().find('different hostname')==-1:
                self.pluginAdapter.Notify('team-ask-server-cert', 'team-update', err, revision)
            
            elif err.lower().find('authorization') != -1:
                self.pluginAdapter.Notify('team-get-authorization', 'team-update', trust, revision)
            else:
                # inak vrat chybovu hlasku
                self.pluginAdapter.Notify('team-exception', err)
    
    
    def IsCompatible(self):
        '''
        Checks if project file is compatible with this VCS. Compatible means it  should not merge
        changes to changed working copy automatic (svn:mime-type application/octet-stream)
        @rtype: bool
        @return: True if it is compatible, False otherwise
        '''
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
        '''
        Hook executed when team plugin demands making project file compatible.
        Makes project file compatible with this VCS. Compatible means it  should not merge
        changes to changed working copy automatic (svn:mime-type application/octet-stream). 
        Should notify team plugin back for reloading project
        
        '''
        command = [self.executable, 'propset', 'svn:mime-type', 'application/octet-stream', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
    
    def IsInConflict(self):
        '''
        Checks if project file is in conflict
        @rtype: bool
        @return: True if it is in conflict, False otherwise 
        '''
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
        '''
        Gets conflicting files
        @rtype: dic
        @return: mine, base and new filenames
        '''
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
        '''
        Hook executed when team plugin demands resolving of VCS conflict. 
        Should notify team plugin back with reloading of project.
        '''
        command = [self.executable, 'resolved', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (result, err) = p.communicate()
        print result, err
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
    
    def SolveConflicts(self):
        '''
        Hook executed when team plugin demands solving conflicts in opened project
        '''
        if self.IsInConflict():
            self.pluginAdapter.Notify('team-solve-conflicts', self.GetConflictingFiles(), self.__fileName)
        else:
            self.pluginAdapter.Notify('team-send-result', 'Project is not in conflict')
    
    
    
    def Checkin(self, username, password, trust , message):
        '''
        Hook executed when team plugin demands checkin. Should notify team plugin back with checkin result
        or with demand for authorization or with demand for server certification trusting or with 
        exception 
        @type username: string
        @param username: username
        @type password: string
        @param password: password
        @type trust: bool
        @param trust: True if server certificate has to be trusted
        @type message: string
        @param message: Checkin message
        '''
        if message is None:
            self.pluginAdapter.Notify('team-exception', 'Message is None')
        
        else:
            command = [self.executable, 'commit', self.__fileName, '-m', message, '--non-interactive']
            if username is not None and password is not None:
                
                command.extend(['--username',username, '--password', password])
            
            if trust:
                command.append('--trust-server-cert')
            p = Popen(command, stdout=PIPE, stderr=PIPE)
            (out, err) = p.communicate()
            if p.returncode == 0:
                self.pluginAdapter.Notify('team-send-result', out)
                
            else:
                if err.lower().find('verification failed') != -1 and err.lower().find('different hostname')==-1:
                    self.pluginAdapter.Notify('team-ask-server-cert', 'team-checkin', err, message)
                if err.lower().find('authorization') != -1:
                    self.pluginAdapter.Notify('team-get-authorization', 'team-checkin', trust, message)
                else:
                    # inak vrat chybovu hlasku
                    self.pluginAdapter.Notify('team-exception', err)
        
    
    def Revert(self):
        '''
        Hook executed when team plugin demands revert. Should notify back with project reload and result.
        '''
        command = [self.executable, 'revert', self.__fileName]
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        p.communicate()
        self.pluginAdapter.Notify('team-load-project', self.__fileName)
        self.pluginAdapter.Notify('team-send-result', 'Reverted')
        
    
    
    def Log(self, username = None, password = None, trust = False):
        '''
        Hook executed when team plugin demands logs. Should notify team plugin back with log result
        or with demand for authorization or with demand for server certification trusting or with 
        exception 
        @type username: string
        @param username: username
        @type password: string
        @param password: password
        @type trust: bool
        @param trust: True if server certificate has to be trusted
        '''
        command = [self.executable, 'log', self.__fileName, '--xml', '--non-interactive']
        
        if username is not None and password is not None:
            command.extend(['--username', username, '--password', password])
            
        if trust:
            command.append('--trust-server-cert')
            
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        (out, err) = p.communicate()
        if p.returncode == 0:
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
            
        else:
            if err.lower().find('verification failed') != -1 and err.lower().find('different hostname')==-1:
                self.pluginAdapter.Notify('team-ask-server-cert', 'team-get-log', err)
            elif err.lower().find('authorization') != -1:
                self.pluginAdapter.Notify('team-get-authorization', 'team-get-log', trust)
            else:
                self.pluginAdapter.Notify('team-exception', err)
            
        
    def Checkout(self, username, password, trust, implId, url, directory, revision = None, ):
        '''
        Hook executed when team plugin demands checkout. Should notify team plugin back with checkout result
        or with demand for authorization or with demand for server certification trusting or with 
        exception 
        @type username: string
        @param username: username
        @type password: string
        @param password: password
        @type trust: bool
        @param trust: True if server certificate has to be trusted
        @type implId: string
        @param implId: Identification of implementation that should perform checkout
        @type url: string
        @param url: Checkout url
        @type directory: string
        @param directory: checkout directory
        @type revision: string
        @param revision: Revision of data
        '''
        if implId == self.ID:
            
            self.checkoutImplId = implId
            
            if revision is None:
                rev = 'HEAD'
            else:
                rev = revision
                
            command = [self.executable, 'checkout', url, directory, '-r', rev, '--non-interactive']
                
            if username is not None and password is not None:
                command.extend(['--username', username, '--password', password])
            
            
            if trust:
                command.append('--trust-server-cert')
                
            p = Popen(command, stdout=PIPE, stderr=PIPE)
            (out, err) = p.communicate()
            
            if p.returncode == 0:
                    self.pluginAdapter.Notify('team-send-result', out)
            else:
                if err.lower().find('verification failed') != -1 and err.lower().find('different hostname')==-1:
                    self.pluginAdapter.Notify('team-ask-server-cert', 'team-checkout', err,implId, url, directory, revision)
                elif err.lower().find('authorization') != -1:
                    self.pluginAdapter.Notify('team-get-authorization', 'team-checkout', trust, implId, url, directory, revision)
                else:
                    self.pluginAdapter.Notify('team-exception', err)
    
    
# select plugin main object
pluginMain = Plugin