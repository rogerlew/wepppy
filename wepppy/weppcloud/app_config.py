
def config_app(app):
    # After 'Create app'
    app.config['MAIL_SERVER'] = 'm.outlook.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'cals-wepp@uidaho.edu'
    app.config['MAIL_PASSWORD'] = '17Ohwhatapassword1'

    app.config['DEBUG'] = True
    app.config['SECRET_KEY'] = '03KHPaE>Q6rv`83s{/JQvf1B$NXRL}Z0s7/;3BmFkY9So%yHL!q|TIe;^8Uon5f'
    app.config['SECURITY_PASSWORD_SALT'] = b'$2b$12$jiwYpqsqzEgv4SNIcG.Aqu'
    app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://wepppy:c0ff33@localhost/wepppy'
    app.config['SECURITY_POST_LOGOUT_VIEW'] = '../weppcloud'
    app.config['SECURITY_POST_LOGIN_VIEW'] = '../weppcloud'
    app.config['SECURITY_POST_REGISTER_VIEW'] = '../weppcloud'
    app.config['SECURITY_EMAIL_SENDER'] = 'cals-wepp@uidaho.edu'
    app.config['SECURITY_CONFIRMABLE'] = True
    app.config['SECURITY_LOGIN_WITHOUT_CONFIRMATION'] = True
    app.config['SECURITY_REGISTERABLE'] = True
    app.config['SECURITY_TRACKABLE'] = True
    app.config['SECURITY_CHANGEABLE'] = True
    app.config['SECURITY_RECOVERABLE'] = True

    app.config['W3W_API_KEY'] = 'XBL7LV7I'

    return app
