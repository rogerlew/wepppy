
def config_app(app):

    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = 'jdskdu29uhr2uh2uheufujhe287'
    app.config['SECURITY_PASSWORD_SALT'] = b'djskhfusdifwuhfsdkjf'
    app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////geodata/weppcloud_runs/standalone.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECURITY_POST_LOGOUT_VIEW'] = '../'
    app.config['SECURITY_POST_LOGIN_VIEW'] = '../'
    app.config['SECURITY_POST_REGISTER_VIEW'] = '../'
    app.config['SITE_PREFIX'] = ''
    app.config['SECURITY_CONFIRMABLE'] = True
    app.config['SECURITY_LOGIN_WITHOUT_CONFIRMATION'] = True
    app.config['SECURITY_REGISTERABLE'] = True
    app.config['SECURITY_TRACKABLE'] = True
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_RECOVERABLE'] = True

    app.config['W3W_API_KEY'] = 'XBL7LV7I'

    return app
