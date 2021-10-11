ip_or_address = 'XX.XXX.XXX.XXX' #testing

proj_directory = 'C:/Users/anars/Downloads/resume_scanner_open_source'

keys_directory = 'C:/Users/anars/Downloads/resume_scanner_open_source'

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True

ALLOWED_HOSTS = [

'*'

]

static_host = 'XX.XXX.XXX.XXX'

static_user = 'ubuntu'

##### Local database #####

databases = {

'default': {

'ENGINE': 'django.db.backends.postgresql_psycopg2',

'NAME': 'referd',

'USER': 'postgres',

'PASSWORD': 'root',

'HOST': 'localhost',

'PORT': '5432',

}

}
