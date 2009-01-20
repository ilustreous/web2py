import uuid, datetime
from gluon.storage import Storage
from gluon.validators import *
from gluon.html import *
from gluon.sqlhtml import *
from gluon.http import *

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
        self.settings=Storage()
        self.settings.server='smtp.gmail.com:587'
        self.settings.sender='you@google.com'
        self.settings.login=None # or 'username:password'

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
        self.errors['captcha']=T('invalid!')
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
             role creation and assingment,
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

    On registration a group with role=new_user.is is created 
    and user is given membership of this group.

    You can create a group with: 

        group_id=auth.add_group('Manager','can access the manage action')
        auth.add_permission(group_id,'access to manage')

    Here "access to manage" is just a user defined string.
    You can give access to a user

        auth.add_membership(group_id,user_id)

    If user id is omitted, it is intended the logged in user

    Then you can decorate a any action

        @auth.requires_permission('access to manage')
        def manage(): return dict()

    You can restict a permission to a specific table 

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
        ### table names to be used
        auth.settings.table_user_name='%s_user' % app
        auth.settings.table_group_name='%s_group' % app
        auth.settings.table_membership_name='%s_membership' % app
        auth.settings.table_permission_name='%s_permission' % app
        auth.settings.table_event_name='%s_event' % app
        ### if none, they will be created
        auth.settings.table_user=None
        auth.settings.table_group=None
        auth.settings.table_membership=None
        auth.settings.table_permission=None
        auth.settings.table_event=None
        ### these should be True or False
        auth.settings.log_login=True
        auth.settings.log_logout=True
        auth.settings.log_registration=True
        auth.settings.log_verify_email=True
        auth.settings.log_profile=True
        auth.settings.log_change_password=True
        auth.settings.log_retrieve_password=True
        auth.settings.log_add_group=True
        auth.settings.log_del_group=True
        auth.settings.log_add_membership=True
        auth.settings.log_del_membership=True
        auth.settings.log_has_membership=False
        auth.settings.log_add_permission=True
        auth.settings.log_del_permission=True
        auth.settings.log_has_permission=False
        ### these should be functions or lambdas
        auth.settings.on_registration=None
        auth.settings.on_login=None
        auth.settings.on_logout=None
        auth.settings.on_profile=None
        auth.settings.on_verify_email=None
        auth.settings.on_retrieve_username=None
        auth.settings.on_retrieve_password=None
        auth.settings.on_change_password=None   
        auth.settings.on_failed_authorization=lambda: raise HTTP(404)
        ### these are messages that can be customized
        auth.messages=Storage()
        auth.messages.logged_in="logged in"
        auth.messages.invalid_email="invalid email"
        auth.messages.invalid_login="invalid login"
        auth.messages.verify_email="click on the link %s to verify your email"
        auth.messages.verify_email_subject="password verify"
        auth.messages.email_verified="email verified"
        auth.messages.username_sent="your username was emailed to you"
        auth.messages.new_password_sent="a new password was emailed to you"
        auth.messages.on_registration_flash="verification email sent"
        auth.messages.invalid_email="Invalid email"
        auth.messages.username_password="you username is: %s"
        auth.messages.username_password_subject="username retrieve"
        auth.messages.retrieve_password="you password is: %s"
        auth.messages.retrieve_password_subject="password retrieve"
        auth.messages.profile_updated="profile updated"
    """

    def __init__(self,environment,db=None):
        """
        auth=Auth(globals(),db)

        - globals() has to be the web2py environment including
          request,response,session
        - db has to be the database where to create tables for authnetication

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
        self.settings=Storage()        
        ### what happens after login?
        self.settings.login_url=URL(r=self.environment.request,
                                    f='user',args='login')
        self.settings.after_login_url=URL(r=self.environment.request,
                                    f='index')
        self.settings.mailer=None
        self.settings.expiration=3600 # seconds
        ### table names to be used
        self.settings.table_user_name='%s_user' % app
        self.settings.table_group_name='%s_group' % app
        self.settings.table_membership_name='%s_membership' % app
        self.settings.table_permission_name='%s_permission' % app
        self.settings.table_event_name='%s_event' % app
        ### if none, they will be created
        self.settings.table_user=None
        self.settings.table_group=None
        self.settings.table_membership=None
        self.settings.table_permission=None
        self.settings.table_event=None
        ### these should be True or False
        self.settings.log_login=True
        self.settings.log_logout=True
        self.settings.log_registration=True
        self.settings.log_verify_email=True
        self.settings.log_profile=True
        self.settings.log_change_password=True
        self.settings.log_retrieve_password=True
        self.settings.log_add_group=True
        self.settings.log_del_group=True
        self.settings.log_add_membership=True
        self.settings.log_del_membership=True
        self.settings.log_has_membership=False
        self.settings.log_add_permission=True
        self.settings.log_del_permission=True
        self.settings.log_has_permission=False
        ### these should be functions or lambdas
        self.settings.on_registration=None
        self.settings.on_login=None
        self.settings.on_logout=None
        self.settings.on_profile=None
        self.settings.on_verify_email=None
        self.settings.on_retrieve_username=None
        self.settings.on_retrieve_password=None
        self.settings.on_change_password=None
        self.settings.on_faild_authorization=lambda: self._HTTP(404)
        ### these are messages that can be customized
        self.messages=Storage()
        self.messages.logged_in="logged in"
        self.messages.invalid_email="invalid email"
        self.messages.invalid_login="invalid login"
        self.messages.verify_email="click on the link %s to verify your email"
        self.messages.verify_email_subject="password verify"
        self.messages.email_verified="email verified"
        self.messages.username_sent="your username was emailed to you"
        self.messages.new_password_sent="a new password was emailed to you"
        self.messages.on_registration_flash="verification email sent"
        self.messages.invalid_email="Invalid email"
        self.messages.username_password="you username is: %s"
        self.messages.username_password_subject="username retrieve"
        self.messages.retrieve_password="you password is: %s"
        self.messages.retrieve_password_subject="password retrieve"
        self.messages.profile_updated="profile updated"

    def _HTTP(self,*a,**b):
        """
        only used in lambda: self._HTTP(404)
        """
        raise HTTP(*a,**b)

    def __call__(self):
        """
        usage:

        def authentcation(): return dict(form=auth())
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

    def login(self):
        """
        returns a login form
        """
        TYPES=(str,int,long,datetime.time,datetime.date,datetime.datetime,bool)
        request=self.environment.request
        session=self.environment.session
        user=self.settings.table_user
        if 'username' in user.fields: username='username'
        else: username='email'
        user[username].requires=IS_NOT_EMPTY()
        form=SQLFORM(user,fields=[username,'password'])
        if FORM.accepts(form,request.vars,session):
            users=self.db(user[username]==form.vars[username])\
                  (user.password==form.vars.password)\
                  (user.registration_key=='')\
                  .select()
            if not users:
                flash=self.messages.invalid_login
                redirect(URL(r=self.environment.request))
            user=Storage(dict([(k,v) for k,v in users[0].items() if isinstance(v,TYPES)]))
            session.auth=Storage(user=user,last_visit=request.now,expiration=self.settings.expiration)
            self.user=user
            session.flash=self.messages.logged_in
            if self.settings.log_login:
                self.log_event('user [%s] logged in' % user.id) 
            redirect(self.settings.after_login_url)
        return form

    def logout(self):
        """
        logout and redirects to login
        """
        if self.settings.log_logout:
            self.log_event('user [%s] logged out' % self.user.id) 
        self.environment.session.auth=None
        redirect(self.settings.login_url)

    def register(self):
        """
        returns a registration form
        """
        form=SQLFORM(self.settings.table_user)
        if self.settings.mailer:
            key=str(uuid.uuid4())
            self.settings.table_user.registration_key.default=key
        if self.settings.captcha!=None:
            form[0].insert(-1,TR('',self.settings.captcha,''))
        if form.accepts(self.environment.request.vars, self.environment.session):
            description='group uniquely assigned to %(first_name)s %(last_name)s' % form.vars
            self.add_membership(self.add_group('Group %s' % form.vars.id,description),form.vars.id)
            self.environment.session.flash=self.messages.on_registration_flash
            if self.settings.mailer:
                if not self.settings.mailer.send(to=form.vars.email,
                     subject=self.messages.verify_email_message,
                     message=self.messages.verify_email % key):
                    self.db.rollback()                     
                    self.environment.response.flash=self.messages.invalid_email
                    return form
            if self.settings.log_register:
                self.log_event('user [%s] registered' % form.vars.id) 
            redirect(self.settings.login_url)
        return form

    def is_logged_in(self):
        """
        checks if the user is logged in and returns True/False.
        if so user is in auth.user as well as in session.auth.user
        """
        if self.environment.session.auth: return True
        return False

    def verify_email(self):
        """
        action user to verify the registration email
        """
        key=self.environment.request.vars.key
        user=self.settings.table_user
        self.db(user.registration_key==key).update(registration_key='')
        self.environment.session.flash=self.messages.email_verified
        if self.settings.log_verify_email:
            self.log_event('user [%s] verified email' % user.id) 
        redirect(self.settings.login_url)

    def retrieve_username(self):
        """
        returns a form to retrieve the user username
        (only if there is a username field)
        """
        user=self.settings.table_user
        if not 'username' in user.fields: raise HTTP(404)
        user.email.requires=[IS_IN_DB(self.db,user.email)]
        form=SQLFORM(user,fields=['email'])
        if FORM.accepts(form,self.environment.request.vars,
                        self.environment.session):
            users=self.db(user.email==form.vars.email)\
                      .select()
            if not users:
                self.environment.session.flash=self.messages.invalid_email
                redirect(URL(r=self.environment.request))
            username=users[0].username
            self.settings.mailer.send(to=form.vars.email,
                subject=self.messages.retrieve_username_message,
                message=self.messages.retrieve_username % username)
            self.environment.session.flash=self.messages.username_sent
            if self.settings.log_retrieve_username:
                self.log_event('user [%s] retrieved username' % users[0].id) 
            redirect(self.settings.login_url)
        return form

    def retrieve_password(self):
        """
        returns a form to retrieve the user password
        """
        user=self.settings.table_user
        user.email.requires=[IS_IN_DB(self.db,user.email)]
        form=SQLFORM(user,fields=['email'])
        if FORM.accepts(form,self.environment.request.vars,
                        self.environment.session):
            users=self.db(user.email==form.vars.email)\
                      .select()
            if not users:
                self.environment.session.flash=self.messages.invalid_email
                redirect(URL(r=self.environment.request))
            password=str(uuid.uuid4())[:8]
            users[0].update_record(password=user.password.validate(password)[0],
                                   registration_key='')
            self.settings.mailer.send(to=form.vars.email,
                subject=self.messages.retrieve_password_message,
                message=self.messages.retrieve_password % password)
            self.environment.session.flash=self.messages.new_password_sent
            if self.settings.log_retrieve_password:
                self.log_event('user [%s] retrieved password' % users[0].id) 
            redirect(self.settings.login_url)
        return form

    def change_password(self):
        """
        returns a form that lets the user change password
        """
        if not self.is_logged_in(): redirect(self.settings.login_url)
        db=self.db
        user=self.settings.table_user
        usern=self.settings.table_user_name
        s=db(user.id==self.user.id)
        pass1=self.environment.request.vars.new_password
        form=form_factory(db.Field('old_password','password',
                      label='Old password',
                      requires=[CRYPT(),IS_IN_DB(s,'%s.password' % usern)]),
                      db.Field('new_password','password',label='New password',
                      requires=[IS_NOT_EMPTY(),CRYPT()]),
                      db.Field('new_password2','password',label='New password',
                      requires=[IS_EXPR('value==%s'%repr(pass1))]))       
        if form.accepts(self.environment.request.vars,
                        self.environment.session):
            s.update(password=form.vars.password)
            self.environment.session.flash=self.messages.password_changed
            if self.settings.log_change_password:
                self.log_event('user [%s] changed password' % auth.user.id) 
            redirect(self.settings.after_login_url)
        return form

    def profile(self):
        """
        returns a form that lets the user change his/her profile
        """
        if not self.is_logged_in(): redirect(self.settings.login_url)
        self.settings.table_user.password.writable=False
        form=SQLFORM(self.settings.table_user,
                     self.user.id)
        if form.accepts(self.environment.request.vars, self.environment.session):
            self.environment.session.flash=self.messages.profile_updated
            if self.settings.log_profile:
                self.log_event('user [%s] edited profile' % auth.user.id) 
            redirect(self.settings.after_login_url)
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
        id=self.settings.table_group.insert(role=role,description=description)
        if self.settings.log_add_group:
            self.log_event('group [%s] created' % id) 
        return id

    def del_group(self,group_id):
        """
        deletes a group
        """
        self.db(self.settings.table_group.id==group_id).delete()
        self.db(self.settings.table_membership.group_id==group_id).delete()
        self.db(self.settings.table_permission.group_id==group_id).delete()
        if self.settings.log_del_group:
            self.log_event('group [%s] deleted' % group_id) 

    def has_membership(self,group_id,user_id=None): 
        """
        checks if user is member of group_id
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        if self.db(membership.user_id==self.user.id)\
                  (membership.group_id==group_id).select(): r=True
        if self.settings.log_has_membership:
            self.log_event('group [%s] membership check: %s' % (group_id,r)) 
        else: r=False
        return r

    def add_membership(self,group_id,user_id=None):
        """
        gives user_id membership of group_id
        if group_id==None than user_id is that of current logged in user
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        id=membership.insert(group_id=group_id,user_id=user_id)
        if self.settings.log_add_membership:
            self.log_event('membership [%s] created for user [%s] in group [%s]' \
            % (id,user_id,group_id)) 
        return id

    def del_membership(self,group_id,user_id=None):
        """
        revokes membership from group_id to user_id
        if group_id==None than user_id is that of current logged in user
        """
        if not user_id: user_id=self.user.id
        membership=self.settings.table_membership
        if self.settings.log_del_membership:
            self.log_event('membership deleted for user [%s] in group [%s]' \
            % (user_id,group_id)) 
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
        if self.settings.log_has_permission:
            self.log_event('check if user [%s] has permission [%s] on [%s:%s]' \
            % (user_id,name,table_name,record_id)) 
        return r

    def add_permission(self,group_id,name='any',table_name='',record_id=0):
        """
        gives group_id 'name' access to 'table_name' and 'record_id'
        """
        permission=self.settings.table_permission
        id=permission.insert(group_id=group_id,name=name,
                                 table_name=str(table_name),
                                 record_id=long(record_id))
        if self.settings.log_add_permission:
            self.log_event('permission [%s] [%s] added for group [%s] on [%s:%s]'\
            % (id,group_id,name,table_name,record_id)) 
        return id

    def del_permission(self,group_id,name='any',table_name='',record_id=0):
        """
        revokes group_id 'name' access to 'table_name' and 'record_id'
        """
        permission=self.settings.table_permission
        if self.settings.log_del_permission:
            self.log_event('permission [%s] deleted for group [%s] on [%s:%s]'\
            % (group_id,name,table_name,record_id)) 
        return self.db(permission.group_id==group_id)\
                      (permission.name==name)\
                      (permission.table_name==str(table_name))\
                      (permission.record_id==long(record_id)).delete()


class Crud(object):
    def __init__(self,environment,db):
        self.environment=Storage(environment)
        self.db=db
        self.settings=Storage()
        self.settings.auth=None
        self.messages=Storage()
    def __call__(self):
        args=self.environment.request.args
        if len(args)<1: raise HTTP(404)
        elif args[0]=='tables' and self.has_permission(*args): return self.tables()
        elif len(args)<2: raise HTTP(404)
        elif args[0]=='create' and self.has_permission(*args): return self.create(args[1])
        elif args[0]=='select' and self.has_permission(*args): return self.select(args[1])
        elif len(args)<3 and self.has_permission(*args): raise HTTP(404)
        elif args[0]=='read' and self.has_permission(*args): return self.read(args[1],args[2])
        elif args[0]=='update' and self.has_permission(*args): return self.update(args[1],args[2])
        elif args[0]=='delete' and self.has_permission(*args): return self.delete(args[1],args[2])
        else: raise HTTP(404)
    def has_permission(self,*args):
        if not self.settings.auth: return True
        return self.settings.auth.has_permission(*args)
    def create(self,table):
        request=self.environment.request
        session=self.environment.session
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        form=SQLFORM(table)      
        if form.accepts(request.vars,session):
            session.flash=self.messages.record_created
            if self.settings.on_create: self.setting.on_create(form)
            redirect('../select/%s' % table)
        return form
    def update(self,table,record):
        request=self.environment.request
        session=self.environment.session
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        form=SQLFORM(table,record)      
        if form.accepts(request.vars,session):
            session.flash=self.messages.record_updated
            if self.settings.on_update: self.setting.on_update(form)
            redirect('../../select/%s' % table)
        return form
    def read(self,table,record):
        request=self.environment.request
        session=self.environment.session
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        form=SQLFORM(table,record,readonly=True)      
        return form
    def delete(self,table,record_id):
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        self.db(table.id==record_id).delete()
        if self.settings.on_delete: self.setting.on_delete(record_id)
        redirect('../../select/%s' % table)
    def select(self,table,query=None,fields=None,orderby=None,limitby=None):
        request=self.environment.request
        if isinstance(table,str):
            if not table in self.db.tables: raise HTTP(404)
            table=self.db[table]
        if not fields: fields=table.fields
        form=SQLTABLE(self.db(query).select(table.ALL,orderby=orderby,limitby=limitby),linkto=URL(r=request,args='read'),upload=URL(r=request,f='download'))
        return form
    def tables(self):
        request=self.environment.request
        return TABLE(*[TR(A(name,_href=URL(r=request,args=('select',name)))) for name in self.db.tables])
"""
fix on_event, onvalidation and next
make better search widget
itemzie and search should handle joins and limitby,orderby
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
