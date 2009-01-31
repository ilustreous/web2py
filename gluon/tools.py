import uuid, datetime, re
from gluon.storage import Storage, Settings
from gluon.validators import *
from gluon.html import *
from gluon.sqlhtml import *
from gluon.http import *

DEFAULT=lambda:None

class Mail(object):
    """
    Class for configuring and sending emails.
    Works with SMTP and Google App Engine

    Example:

    from gluon.contrib.utils import *
    mail=Mail()
    mail.settings.server='smtp.gmail.com:587'
    mail.sender='you@somewhere.com'
    mail.login=None or 'username:password'
    mail.send(to=['you@whatever.com'],subject='None',message='None')

    In Google App Engine use mail.settings.server='gae'
    """

    def __init__(self):
        self.settings=Settings()
        self.settings.server='smtp.gmail.com:587'
        self.settings.sender='you@google.com'
        self.settings.login=None # or 'username:password'
        self.settings.lock_keys=True

    def send(self,to,subject='None',message='None'):
        """
        Sends an email. Returns True on success, False on failure.
        """
        if not isinstance(to,list): to=[to]
        try:
            if self.settings.server=='gae':
                from google.appengine.api import mail
                mail.send_mail(sender=self.settings.sender,
                               to=to,
                               subject=subject,
                               body=message)
            else:
                msg="From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s" % \
                    (self.settings.sender,\
                    ", ".join(to),subject,message)
                import smtplib, socket
                host, port=self.settings.server.split(':')
                server = smtplib.SMTP(host,port)
                if self.settings.login:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    username, password=self.settings.login.split(':')
                    server.login(username, password)
                server.sendmail(self.settings.sender, to, msg)
                server.quit()
        except Exception,e: return False
        return True

class RECAPTCHA(DIV):
    API_SSL_SERVER="https://api-secure.recaptcha.net"
    API_SERVER="http://api.recaptcha.net"
    VERIFY_SERVER="api-verify.recaptcha.net"
    def __init__(self,request,public_key='',private_key='',use_ssl=False,error=None,error_message='invalid'):
        self.remote_addr=request.env.remote_addr
        self.public_key=public_key
        self.private_key=private_key
        self.use_ssl=use_ssl
        self.error=error
        self.errors=Storage()
        self.error_message=error_message
        self.components=[]
        self.attributes={}        
    def _validate(self):
        # for local testing:
        import urllib2, urllib
        recaptcha_challenge_field=self.request_vars.recaptcha_challenge_field
        recaptcha_response_field=self.request_vars.recaptcha_response_field
        private_key=self.private_key
        remoteip=self.remote_addr
        if not (recaptcha_response_field and recaptcha_challenge_field and
           len (recaptcha_response_field) and len (recaptcha_challenge_field)):
            self.errors['captcha']=self.error_message
            return False
        params = urllib.urlencode ({
            'privatekey': private_key,
            'remoteip' : remoteip,
            'challenge': recaptcha_challenge_field,
            'response' : recaptcha_response_field,
            })
        request = urllib2.Request (
            url = "http://%s/verify" % self.VERIFY_SERVER,
            data = params,
            headers = {
              "Content-type": "application/x-www-form-urlencoded",
              "User-agent": "reCAPTCHA Python"
            })
        httpresp = urllib2.urlopen (request)
        return_values = httpresp.read ().splitlines ();
        httpresp.close();
        return_code = return_values[0]
        if return_code=="true":
            del self.request_vars.recaptcha_challenge_field
            del self.request_vars.recaptcha_response_field
            self.request_vars.captcha=''
            return True
        self.errors['captcha']='invalid!'
        return False
    def xml(self):
        public_key=self.public_key
        use_ssl=self.use_ssl,
        error_param = ''
        if self.error: error_param = '&error=%s' % self.error
        if use_ssl: server = self.API_SSL_SERVER
        else: server = self.API_SERVER
        captcha="""<script type="text/javascript" src="%(ApiServer)s/challenge?k=%(PublicKey)s%(ErrorParam)s"></script>
<noscript>
<iframe src="%(ApiServer)s/noscript?k=%(PublicKey)s%(ErrorParam)s" height="300" width="500" frameborder="0"></iframe><br />
<textarea name="recaptcha_challenge_field" rows="3" cols="40"></textarea>
<input type='hidden' name='recaptcha_response_field' value='manual_challenge' />
</noscript>
""" % {'ApiServer' : server,'PublicKey' : public_key,'ErrorParam' : error_param }   
        if not self.errors.captcha: return captcha
        else: return captcha+DIV(self.errors['captcha'],_class='error').xml()

class Auth(object):
    """
    Class for authentication, authorization, role based access control
    Includes registration, login, logout, profile, 
             username and password retrieval, event logging
             role creation and assignment,
             user defined group/role based permission
    
    Authentication Example:
    
    from gluon.contrib.utils import *
    mail=Mail()
    mail.settings.server='smtp.gmail.com:587'
    mail.settings.sender='you@somewhere.com'
    mail.settings.login='username:password'
    auth=Auth(globals(),db)
    auth.settings.mailer=mail
    # auth.settings....=...
    auth.define_tables()
    def authentication(): return dict(form=auth())
  
    exposes:
    - http://.../{application}/{controller}/authentication/login
    - http://.../{application}/{controller}/authentication/logout
    - http://.../{application}/{controller}/authentication/register
    - http://.../{application}/{controller}/authentication/veryfy_email
    - http://.../{application}/{controller}/authentication/retrieve_username
    - http://.../{application}/{controller}/authentication/retrieve_password
    - http://.../{application}/{controller}/authentication/profile
    - http://.../{application}/{controller}/authentication/change_password

    On registration a group with role=new_user.id is created 
    and user is given membership of this group.

    You can create a group with: 

        group_id=auth.add_group('Manager','can access the manage action')
        auth.add_permission(group_id,'access to manage')

    Here "access to manage" is just a user defined string.
    You can give access to a user

        auth.add_membership(group_id,user_id)

    If user id is omitted, it is intended the logged in user

    Then you can decorate any action

        @auth.requires_permission('access to manage')
        def manage(): return dict()

    You can restrict a permission to a specific table 

        auth.add_permission('edit',db.sometable)
        @auth.requires_permission('edit',db.sometable)

    Or to a specific record
    
        auth.add_permission('edit',db.sometable,45)
        @auth.requires_permission('edit',db.sometable,45)

    If authorization is not granted calls

        auth.settings.on_failed_authorization=lambda: raise HTTP(404)

    Other options:

        auth.settings.mailer=None
        auth.settings.expiration=3600 # seconds

        ...

        ### these are messages that can be customized
        ...
    """

    def __init__(self,environment,db=None):
        """
        auth=Auth(globals(),db)

        - globals() has to be the web2py environment including
          request,response,session
        - db has to be the database where to create tables for authentication

        """
        self.environment=Storage(environment)
        self.db=db
        request=self.environment.request
        session=self.environment.session
        app=request.application
        auth=session.auth
        if auth and auth.last_visit and \
           auth.last_visit+datetime.timedelta(days=0,seconds=auth.expiration)>request.now:
            self.user=auth.user
            auth.last_visit=request.now
        else:
            self.user=None
            session.auth=None
        self.settings=Settings()        
        ### what happens after login?
        self.settings.login_url=URL(r=self.environment.request,
                                    f='user',args='login')
        self.settings.after_login_url=URL(r=self.environment.request,
                                    f='index')
        self.settings.mailer=None
        self.settings.expiration=3600 # seconds
        ### table names to be used
        self.settings.table_user_name='auth_user'
        self.settings.table_group_name='auth_group'
        self.settings.table_membership_name='auth_membership'
        self.settings.table_permission_name='auth_permission'
        self.settings.table_event_name='auth_event'
        ### if none, they will be created
        self.settings.table_user=None
        self.settings.table_group=None
        self.settings.table_membership=None
        self.settings.table_permission=None
        self.settings.table_event=None
        ### 
        self.settings.register_log='User %(id)s Registered'
        self.settings.login_log='User %(id)s Logged-in'
        self.settings.logout_log='User %(id)s Logged-out'
        self.settings.profile_log='User %(id)s Profile updated'
        self.settings.verify_email_log='User %(id)s Verification email sent'
        self.settings.retrieve_username_log='User %(id)s Username retrieved'
        self.settings.retrieve_password_log='User %(id)s Password retrieved'
        self.settings.change_password_log='User %(id)s Password changed'
        self.settings.add_group_log='Group %(group_id)s created'
        self.settings.del_group_log='Group %(group_id)s deleted'
        self.settings.add_membership_log=None
        self.settings.del_membership_log=None
        self.settings.has_membership_log=None
        self.settings.add_permission_log=None
        self.settings.del_permission_log=None
        self.settings.has_permission_log=None
        
        self.settings.showid=False
        ### these should be functions or lambdas
        self.settings.login_next=URL(r=request,f='index')
        self.settings.login_onvalidation=None
        self.settings.login_onaccept=None
        
        self.settings.register_next=URL(r=request,f='user',args='login')
        self.settings.register_onvalidation=None
        self.settings.register_onaccept=None
        
        self.settings.verify_email_next=URL(r=request,f='user',args='login')
        self.settings.verify_email_onvalidation=None
        self.settings.verify_email_onaccept=None
        
        self.settings.submit_button='Submit'
        self.settings.delete_label='Check to delete:'
        ### these are messages that can be customized
        self.messages=Settings()
        self.messages.logged_in="Logged in"
        self.messages.email_sent="Email sent"
        self.messages.email_verified="Email verified"
        self.messages.logged_out="Logged out"
        self.messages.registration_succesful="Registration successful"
        self.messages.invalid_email="Invalid email"
        self.messages.invalid_login="Invalid login"
        self.messages.verify_email="Click on the link http://...verify_email/%(key)s to verify your email"
        self.messages.verify_email_subject="Password verify"
        self.messages.username_sent="Your username was emailed to you"
        self.messages.new_password_sent="A new password was emailed to you"
        self.messages.invalid_email="Invalid email"
        self.messages.password_changed="Password changed"
        self.messages.retrieve_username="Your username is: %(username)s"
        self.messages.retrieve_username_subject="Username retrieve"
        self.messages.retrieve_password="Your password is: %(password)s"
        self.messages.retrieve_password_subject="Password retrieve"
        self.messages.profile_updated="Profile updated"
        self.messages.lock_keys=True

    def _HTTP(self,*a,**b):
        """
        only used in lambda: self._HTTP(404)
        """
        raise HTTP(*a,**b)

    def __call__(self):
        """
        usage:

        def authentication(): return dict(form=auth())
        """
        args=self.environment.request.args
        if not args: redirect(URL(r=self.environment.request,args='login'))
        elif args[0]=='login': return self.login() 
        elif args[0]=='logout': return self.logout()
        elif args[0]=='register': return self.register() 
        elif args[0]=='verify_email': return self.verify_email() 
        elif args[0]=='retrieve_username': return self.retrieve_username()
        elif args[0]=='retrieve_password': return self.retrieve_password()
        elif args[0]=='change_password': return self.change_password()
        elif args[0]=='profile': return self.profile()
        elif args[0]=='groups': return self.groups() 
        else: raise HTTP(404)

    def define_tables(self):
        """
        to be called unless tables are defined manually
        """
        db=self.db
        if not self.settings.table_user: 
            self.settings.table_user=\
               db.define_table(self.settings.table_user_name,
               db.Field('first_name'),
               db.Field('last_name'),
               # db.Field('username'), ### if present will be used for login
               db.Field('email'),
               db.Field('password','password',readable=False),
               db.Field('registration_key',writable=False,readable=False))
        table=self.settings.table_user
        table.first_name.requires=IS_NOT_EMPTY()
        table.last_name.requires=IS_NOT_EMPTY()
        table.password.requires=CRYPT()
        table.email.requires=[
            IS_EMAIL(),
            IS_NOT_IN_DB(db,'%s.email' % self.settings.table_user._tablename)]
        table.registration_key.default=''
        if not self.settings.table_group: 
            self.settings.table_group=\
               db.define_table(self.settings.table_group_name,
               db.Field('role'),
               db.Field('description','text'))
        table=self.settings.table_group
        table.role.requires= \
            IS_NOT_IN_DB(db,'%s.role' % self.settings.table_group._tablename)
        if not self.settings.table_membership: 
            self.settings.table_membership=\
               db.define_table(self.settings.table_membership_name,
               db.Field('user_id',self.settings.table_user),
               db.Field('group_id',self.settings.table_group))
        table=self.settings.table_membership
        table.user_id.requires= \
           IS_IN_DB(db,'%s.id' % self.settings.table_user._tablename,'%(id)s: %(first_name)s %(last_name)s')
        table.group_id.requires= \
           IS_IN_DB(db,'%s.id' % self.settings.table_group._tablename,'%(id)s: %(role)s')
        if not self.settings.table_permission: 
            self.settings.table_permission=\
               db.define_table(self.settings.table_permission_name,
               db.Field('group_id'),
               db.Field('name',default='default'),
               db.Field('table_name'),
               db.Field('record_id','integer'))
        table=self.settings.table_permission
        table.group_id.requires= \
           IS_IN_DB(db,'%s.id' % self.settings.table_group._tablename,'%(id)s: %(role)s')
        table.name.requires=IS_NOT_EMPTY()
        table.table_name.requires=IS_IN_SET(self.db.tables)
        table.record_id.requires=IS_INT_IN_RANGE(0,10**9)
        if not self.settings.table_event: 
            self.settings.table_event=\
               db.define_table(self.settings.table_event_name,
               db.Field('time_stamp','datetime',default=self.environment.request.now),
               db.Field('client_ip',default=self.environment.request.client),
               db.Field('user_id',self.settings.table_user,default=0),
               db.Field('origin',default='auth'),
               db.Field('description','text',default=''))
        table=self.settings.table_event
        table.user_id.requires= \
           IS_IN_DB(db,'%s.id' % self.settings.table_user._tablename,'%(id)s: %(first_name)s %(last_name)s\
')
        table.origin.requires=IS_NOT_EMPTY()
        table.description.requires=IS_NOT_EMPTY()

    def log_event(self,description,origin='auth'):
        """
        usage:
        
        auth.log_event(description='this happened',origin='auth')
        """
        if self.is_logged_in(): user_id=self.user.id
        else: user_id=0 # user unknown
        self.settings.table_event.insert(description=description,
                                         origin=origin,user_id=user_id)    

    def login(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a login form
        """
        user=self.settings.table_user
        if 'username' in user.fields: username='username'
        else: username='email'
        user[username].requires=IS_NOT_EMPTY()
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.login_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.login_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.login_onaccept
        if log==DEFAULT:
             log=self.settings.login_log
        form=SQLFORM(user,fields=[username,'password'],
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_button,
                     delete_label=self.settings.delete_label)
        if FORM.accepts(form,request.vars,session,onvalidation=onvalidation):
            ### BEGIN
            TYPES=(str,int,long,datetime.time,datetime.date,
                   datetime.datetime,bool)
            users=self.db(user[username]==form.vars[username])\
                  (user.password==form.vars.password)\
                  (user.registration_key=='')\
                  .select()
            if not users:
                session.flash=self.messages.invalid_login
                redirect(URL(r=request))
            user=Storage(dict([(k,v) for k,v in users[0].items() \
                         if isinstance(v,TYPES)]))
            session.auth=\
                Storage(user=user,last_visit=request.now,
                expiration=self.settings.expiration)
            self.user=user
            session.flash=self.messages.logged_in
            log=self.settings.login_log
            if log:
                self.log_event(log % self.user)
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def logout(self,next=DEFAULT,onlogout=DEFAULT):
        """
        logout and redirects to login
        """
        if next==DEFAULT: next=self.settings.login_url 
        if onlogout==DEFAULT: onlogout=self.settings.logout_onlogout
        if onlogout: onlogout(self.user)
        log=self.settings.logout_log
        if log:
            self.log_event(log % self.user) 
        self.environment.session.auth=None
        self.environment.session.flash=self.messages.logged_out
        redirect(next or self.settings.next)

    def register(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a registration form
        """
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.register_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.register_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.register_onaccept
        if log==DEFAULT:
             log=self.settings.register_log
        user=self.settings.table_user
        form=SQLFORM(user,
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_button,
                     delete_label=self.settings.delete_label)
        key=str(uuid.uuid4())
        if form.accepts(request.vars,session,onvalidation=onvalidation):
            description='group uniquely assigned to %(first_name)s %(last_name)s' % form.vars
            group_id=self.add_group(form.vars.id,description)
            self.add_membership(group_id,form.vars.id)
            if self.settings.mailer:
                user[form.vars.id]=dict(registration_key=key)
                if not self.settings.mailer.send(to=form.vars.email,
                     subject=self.messages.verify_email_subject,
                     message=self.messages.verify_email % dict(key=key)):
                    self.db.rollback()                     
                    session.flash=self.messages.invalid_email
                    return form
                session.flash=self.messages.email_sent
            else:
                session.flash=self.messages.registration_succesful    
            log=self.settings.register_log
            if log:
                self.log_event(log % form.vars)
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def is_logged_in(self):
        """
        checks if the user is logged in and returns True/False.
        if so user is in auth.user as well as in session.auth.user
        """
        if self.environment.session.auth:
            return True
        return False

    def verify_email(self,next=DEFAULT,onaccept=DEFAULT,log=DEFAULT):
        """
        action user to verify the registration email, XXXXXXXXXXXXXXXX
        """
        key=self.environment.request.args[-1]
        user=self.settings.table_user
        users=self.db(user.registration_key==key).select()
        if not users: raise HTTP(404)
        user=users[0]
        user.update_record(registration_key='')
        self.environment.session.flash=self.messages.email_verified
        if log==DEFAULT: log=self.settings.verify_email_log
        if next==DEFAULT: next=self.settings.verify_email_next
        if onaccept==DEFAULT:
            onaccept=self.settings.verify_email_onaccept
        if log:
            self.log_event(log % user) 
        if onaccept:
            onaccept(user)
        redirect(next)

    def retrieve_username(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a form to retrieve the user username
        (only if there is a username field)
        """
        user=self.settings.table_user
        if not 'username' in user.fields: raise HTTP(404)
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.retrieve_username_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.retrieve_username_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.retrieve_username_onaccept
        if log==DEFAULT:
             log=self.settings.retrieve_username_log
        user.email.requires=[IS_IN_DB(self.db,user.email)]
        form=SQLFORM(user,fields=['email'],
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_botton,
                     delete_label=self.settings.delete_label)
        if FORM.accepts(form,request.vars,session,onvalidation=onvalidation):
            users=self.db(user.email==form.vars.email)\
                      .select()
            if not users:
                self.environment.session.flash=self.messages.invalid_email
                redirect(URL(r=self.environment.request))
            username=users[0].username
            self.settings.mailer.send(to=form.vars.email,
                subject=self.messages.retrieve_username_subject,
                message=self.messages.retrieve_username % dict(username=username))
            session.flash=self.messages.email_sent
            log=self.settings.retrieve_username_log
            if log:
                self.log_event(log % users[0])
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form


    def retrieve_password(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a form to retrieve the user password
        """
        user=self.settings.table_user
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.retrieve_password_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.retrieve_password_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.retrieve_password_onaccept
        if log==DEFAULT:
             log=self.settings.retrieve_password_log
        user.email.requires=[IS_IN_DB(self.db,user.email)]
        form=SQLFORM(user,fields=['email'],
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_botton,
                     delete_label=self.settings.delete_label)
        if FORM.accepts(form,request.vars,session,onvalidation=onvalidation):
            users=self.db(user.email==form.vars.email)\
                      .select()
            if not users:
                self.environment.session.flash=self.messages.invalid_email
                redirect(URL(r=self.environment.request))
            password=str(uuid.uuid4())[:8]
            users[0].update_record(password=user.password.validate(password)[0],
                                   registration_key='')
            self.settings.mailer.send(to=form.vars.email,
                subject=self.messages.retrieve_password_subject,
                message=self.messages.retrieve_password % dict(password=password))
            session.flash=self.messages.email_sent
            log=self.settings.retrieve_password_log
            if log:
                self.log_event(log % users[0])
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def change_password(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a form that lets the user change password
        """
        if not self.is_logged_in(): redirect(self.settings.login_url)
        db=self.db
        user=self.settings.table_user
        usern=self.settings.table_user_name
        s=db(user.id==self.user.id)
        pass1=self.environment.request.vars.new_password
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.change_password_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.change_password_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.change_password_onaccept
        if log==DEFAULT:
             log=self.settings.change_password_log
        form=form_factory(db.Field('old_password','password',
                      label='Old password',
                      requires=[CRYPT(),IS_IN_DB(s,'%s.password' % usern)]),
                      db.Field('new_password','password',label='New password',
                      requires=[IS_NOT_EMPTY(),CRYPT()]),
                      db.Field('new_password2','password',label='New password',
                      requires=[IS_EXPR('value==%s'%repr(pass1))]))       
        if form.accepts(request.vars,session,onvalidation=onvalidation):
            s.update(password=form.vars.password)
            session.flash=self.messages.password_changed
            log=self.settings.change_password_log
            if log:
                self.log_event(log % self.user)
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def profile(self,next=DEFAULT,onvalidation=DEFAULT,
                      onaccept=DEFAULT,log=DEFAULT):
        """
        returns a form that lets the user change his/her profile
        """
        if not self.is_logged_in(): redirect(self.settings.login_url)
        self.settings.table_user.password.writable=False
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.profile_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.profile_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.profile_onaccept
        if log==DEFAULT:
             log=self.settings.profile_log
        form=SQLFORM(self.settings.table_user,self.user.id,
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_botton,
                     delete_label=self.settings.delete_label)
        if form.accepts(request.vars,session,onvalidation=onvalidation):
            session.flash=self.messages.profile_updated
            log=self.settings.profile_log
            if log:
                self.log_event(log % self.user)
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def groups(self):
        """
        displays the groups and their roles for the logged in user
        """
        if not self.is_logged_in(): redirect(self.settings.login_url)
        memberships=self.db(self.settings.table_membership.user_id==self.user.id).select()
        table=TABLE()
        for membership in memberships:
            groups=self.db(self.settings.table_group.id==membership.group_id).select()            
            if groups:
                group=groups[0]
                table.append(TR(H3(group.role,'(%s)' % group.id)))
                table.append(TR(P(group.description)))
        if not memberships: return None
        return table

    def requires_login(self):
        """
        decorator that prevents access to action if not logged in
        """
        def decorator(action):
            def f(*a,**b):
                if not self.is_logged_in(): redirect(self.settings.login_url)
                return action(*a,**b)
            return f
        return decorator

    def requires_membership(self,group_id):
        """
        decorator that prevents access to action if not logged in or
        if user logged in is not a member of group_id
        """
        def decorator(action):
            def f(*a,**b):
                if not self.is_logged_in(): redirect(self.settings.login_url)
                if not self.has_membership(group_id):
                    self.settings.on_failed_authorization()
                return action(*a,**b)
            return f
        return decorator

    def requires_permission(self,name,table_name='',record_id=0):
        """
        decorator that prevents access to action if not logged in or
        if user logged in is not a member of any group (role) that
        has 'name' access to 'table_name', 'record_id'.
        """
        def decorator(action):
            def f(*a,**b):
                if not self.is_logged_in(): redirect(self.settings.login_url)
                if not self.has_permission(name,table_name,record_id):
                    self.settings.on_failed_authorization()
                return action(*a,**b)
            return f
        return decorator

    def add_group(self,role,description=''):
        """
        creates a group associated to a role
        """
        group_id=self.settings.table_group.insert(role=role,description=description)
        log=self.settings.add_group_log
        if log: self.log_event(log % dict(group_id=group_id,role=role)) 
        return group_id

    def del_group(self,group_id):
        """
        deletes a group
        """
        self.db(self.settings.table_group.id==group_id).delete()
        self.db(self.settings.table_membership.group_id==group_id).delete()
        self.db(self.settings.table_permission.group_id==group_id).delete()
        log=self.settings.del_group_log
        if log: self.log_event(log % dict(group_id=group_id))

    def has_membership(self,group_id,user_id=None): 
        """
        checks if user is member of group_id
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        if self.db((membership.user_id==user_id) & (membership.group_id==group_id)).select():
            r=True
        else:
            r=False
        log=self.settings.has_membership_log
        if log: self.log_event(log % dict(group_id=group_id,check=r)) 
        return r

    def add_membership(self,group_id,user_id=None):
        """
        gives user_id membership of group_id
        if group_id==None than user_id is that of current logged in user
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        id=membership.insert(group_id=group_id,user_id=user_id)
        log=self.settings.add_membership_log
        if log: self.log_event(log % dict(user_id=user_id,group_id=group_id))
        return id

    def del_membership(self,group_id,user_id=None):
        """
        revokes membership from group_id to user_id
        if group_id==None than user_id is that of current logged in user
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        log=self.settings.del_membership_log
        if log: self.log_event(log % dict(user_id=user_id,group_id=group_id)) 
        return self.db(membership.user_id==user_id)\
                      (membership.group_id==group_id).delete()

    def has_permission(self,name='any',table_name='',record_id=0,user_id=None):
        """
        checks if user_id or current logged in user is member of a group
        that has 'name' permission on 'table_name' and 'record_id'
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        rows=self.db(membership.user_id==user_id).select(membership.group_id)
        groups=set([row.group_id for row in rows])
        permission=self.settings.table_permission
        rows=self.db(permission.name==name)\
                        (permission.table_name==str(table_name))\
                        (permission.record_id==record_id)\
                        .select(permission.group_id)
        groups_required=set([row.group_id for row in rows])
        if record_id:
            rows=self.db(permission.name==name)\
                        (permission.table_name==str(table_name))\
                        (permission.record_id==0)\
                        .select(permission.group_id)
            groups_required=groups_required.union(set([row.group_id for row in rows]))
        if groups.intersection(groups_required): r=True
        else: r=False
        log=self.settings.has_permission_log
        if log: self.log_event(log % dict(user_id=user_id,name=name,table_name=table_name,record_id=record_id))
        return r

    def add_permission(self,group_id,name='any',table_name='',record_id=0):
        """
        gives group_id 'name' access to 'table_name' and 'record_id'
        """
        permission=self.settings.table_permission
        id=permission.insert(group_id=group_id,name=name,
                                 table_name=str(table_name),
                                 record_id=long(record_id))
        log=self.settings.add_permission_log
        if log: self.log_event(log % dict(permission_id,group_id=group_id,name=name,table_name=table_name,record_id=record_id)) 
        return id

    def del_permission(self,group_id,name='any',table_name='',record_id=0):
        """
        revokes group_id 'name' access to 'table_name' and 'record_id'
        """
        permission=self.settings.table_permission
        log=self.settings.del_permission_log
        if log: self.log_event(log % dict(group_id=group_id,name=name,table_name=table_name,record_id=record_id)) 
        return self.db(permission.group_id==group_id)\
                      (permission.name==name)\
                      (permission.table_name==str(table_name))\
                      (permission.record_id==long(record_id)).delete()


class Crud(object):
    def __init__(self,environment,db):
        self.environment=Storage(environment)
        self.db=db
        request=self.environment.request
        self.settings=Settings()
        self.settings.auth=None
        self.settings.logger=None
        self.settings.submit_button='Submit'
        self.settings.delete_label='Check to delete:'
        self.settings.update_log='Record %(id)s updated'
        self.settings.create_log='Record %(id)s created'
        self.settings.read_log='Record %(id)s read'
        self.settings.delete_log='Record %(id)s deleted'

        self.settings.create_next=URL(r=request)
        self.settings.update_next=URL(r=request)
        self.settings.delete_next=URL(r=request)
        self.settings.create_onvalidation=None
        self.settings.update_onvalidation=None
        self.settings.create_onaccept=None
        self.settings.update_onaccept=None
        self.settings.delete_onaccept=None
        self.settings.showid=False
        self.settings.lock_keys=True
        self.messages=Storage()
        self.messages.record_created="Record Created"
        self.messages.record_updated="Record Updated"
        self.messages.record_deleted="Record Deleted"
        self.messages.lock_keys=True
    def __call__(self):
        args=self.environment.request.args
        if len(args)<1:
            redirect(URL(r=self.environment.request,args='tables'))
        elif args[0]=='tables' and self.has_permission(*args):
            return self.tables()
        elif len(args)<2:
            raise HTTP(404)
        elif args[0]=='create' and self.has_permission(*args):
            return self.create(args[1])
        elif args[0]=='select' and self.has_permission(*args):
            return self.select(args[1])
        elif len(args)<3 and self.has_permission(*args):
            raise HTTP(404)
        elif args[0]=='read' and self.has_permission(*args):
            return self.read(args[1],args[2])
        elif args[0]=='update' and self.has_permission(*args):
            return self.update(args[1],args[2])
        elif args[0]=='delete' and self.has_permission(*args):
            return self.delete(args[1],args[2])
        else:
            raise HTTP(404)
    def log_event(self,message):
        if self.settings.logger: self.settings.logger.log_event(message,'crud')
    def has_permission(self,*args):
        if not self.settings.auth: return True
        return self.settings.auth.has_permission(*args)
    def tables(self):
        request=self.environment.request
        return TABLE(*[TR(A(name,_href=URL(r=request,args=('select',name)))) \
                       for name in self.db.tables])

    def update(self,table,record,next=DEFAULT,onvalidation=DEFAULT,
                          onaccept=DEFAULT,log=DEFAULT,message=DEFAULT):
        request=self.environment.request
        session=self.environment.session
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        if next==DEFAULT:
             next=request.vars._next or self.settings.update_next
        if onvalidation==DEFAULT:
             onvalidation=self.settings.update_onvalidation
        if onaccept==DEFAULT:
             onaccept=self.settings.update_onaccept
        if log==DEFAULT:
             log=self.settings.update_log
        if message==DEFAULT:
            message=self.messages.record_updated
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        form=SQLFORM(table,record,
                     upload=URL(r=request,f='download'),
                     hidden=dict(_next=request.vars._next),
                     showid=self.settings.showid,
                     submit_button=self.settings.submit_button,
                     delete_label=self.settings.delete_label)
        if form.accepts(request.vars,session,onvalidation=onvalidation):
            session.flash=message
            log=self.settings.update_log
            if log:
                self.log_event(log % form)
            if onaccept:
                onaccept(form)
            if not next:
                next=URL(r=request)
            elif next and not next[0]=='/' and next[:4]!='http':
                next=URL(r=request,f=next.replace('[id]',str(form.vars.id)))
            redirect(next)
        return form

    def create(self,table,next=DEFAULT,onvalidation=DEFAULT,
                          onaccept=DEFAULT,log=DEFAULT):
        if next==DEFAULT:
            next=self.settings.create_next
        if onvalidation==DEFAULT:
            onvalidation=self.settings.create_onvalidation
        if onaccept==DEFAULT:
            onaccept=self.settings.create_onaccept
        if log==DEFAULT:
            log=self.settings.create_log
        return self.update(table,None,next,onvalidation,onaccept,log)

    def read(self,table,record):
        request=self.environment.request
        session=self.environment.session
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        form=SQLFORM(table,record,readonly=True,comments=False,
                     upload=URL(r=request,f='download'),
                     showid=self.settings.showid)
        return form

    def delete(self,table,record_id,next=DEFAULT):
        request=self.environment.request
        session=self.environment.session
        if next==DEFAULT: next=self.settings.delete_next
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        if not request.vars._next:
            request.vars._next=request.env.http_referer or ''
        record=table[record_id]
        if record:
           del table[record_id]
           if self.settings.delete_onaccept: self.settings.delete_onaccept(record)
           session.flash=self.messages.record_deleted
        redirect(next)

    def select(self,table,query=None,fields=None,orderby=None,limitby=None,**attr):
        request=self.environment.request
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        if not query: query=table.id>0
        if not fields: fields=[table.ALL]
        if not attr.has_key('linkto'): attr['linkto']=URL(r=request,args='read')
        if not attr.has_key('upload'): attr['upload']=URL(r=request,f='download')
        return SQLTABLE(self.db(query).select(*fields,**dict(orderby=orderby,limitby=limitby)),**attr)

def fetch(url):
    try:
        from google.appengine.api.urlfetch import fetch
        if url.find('?')>=0:
            url,payload=url.split('?')
            return fetch(url,payload=payload).content
        return fetch(url).content
    except:
        import urllib
        return urllib.urlopen(url).read()

regex_geocode=re.compile('\<coordinates\>(?P<la>[^,]*),(?P<lo>[^,]*).*?\</coordinates\>')
def geocode(address):
    import re, urllib
    try:
        a=urllib.quote(address)
        txt=fetch('http://maps.google.com/maps/geo?q=%s&output=xml'%a)
        item=regex_geocode.search(txt)
        la,lo=float(item.group('la')),float(item.group('lo'))
        return la,lo
    except: return 0.0,0.0


"""
to do:

all with SQLFORM should redirect to next or _sender or 'index'

                    on_*    on_*_validation messages.on_*  log
login               y       n               y              y
register            y       y               y              y (enable/disable)
verify_email
profile             y       y               y              y
retrieve_username   y       n               y              y
retrieve_password   y       n               y              y
change_password     y       n               y              y
logout                                                     y
groups

create              y       y               y              n
update              y       y               y              n
delete              y       n               y              n
tables
select

Merge select with itemize from t2
"""        

"""
print 'creating db'
db=SQLDB()
print 'new auth'
auth=Auth(globals(),db)
print 'define tables'
auth.define_tables()
print 'define action'
@auth.requires_permission('any',auth.settings.table_user)
def authorization(a=7): return dict(form=auth())
print 'create user'
user_id=auth.settings.table_user.insert(first_name='Massimo')
print 'create group'
group_id=auth.add_group('Manager')
print 'checking membership and permissions'
print auth.add_membership(group_id,user_id)
print auth.add_permission(group_id,'any',auth.settings.table_user,0)
print auth.has_permission('any',auth.settings.table_user,3,user_id)
print 'delete permission'
auth.del_permission('any',auth.settings.table_user,0)
print 'delete membership'
auth.del_membership(group_id,user_id)
"""
