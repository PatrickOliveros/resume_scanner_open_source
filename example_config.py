proj_directory = 'C:/Users/anars/Downloads/resume_scanner_open_source'

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True

ALLOWED_HOSTS = [

'*'

]

static_host = 'XX.XXX.XXX.XXX'

static_user = 'ubuntu'

##### Local database #####

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydatabase',
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
