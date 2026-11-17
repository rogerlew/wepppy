"""Render synthetic auth/profile HTML for a local browser layout check."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
from flask import render_template

root=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('auth_form_fixtures',root/'tests/weppcloud/routes/test_security_auth_forms.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app=module.security_template_app.__wrapped__()
out=root/'.cilogon-ui-preview'
out.mkdir(exist_ok=True)
providers={name:{'name':name.capitalize()} for name in ('google','github','cilogon')}
with app.test_request_context():
    html=render_template('security/login_user.html',login_user_form=module._LoginForm(),enabled_oauth_providers=providers,identity_attributes=['email'])
    (out/'login.html').write_text(html)
    for kind in ('shared','cilogon'):
        user=SimpleNamespace(id=7,account_kind=kind,local_credential_state='legacy' if kind=='shared' else 'none',
            email='a-very-long-address-for-mobile-layout-testing@example.com' if kind=='shared' else None,
            contact_email='a-very-long-contact-address-for-mobile-layout-testing@example.com',
            first_name='Example',last_name='Person',roles=[],mailbox_verified_at=None,
            oauth_accounts=SimpleNamespace(all=lambda:[SimpleNamespace(id=1,provider='google' if kind=='shared' else 'cilogon',email=None)]))
        html=render_template('user/profile.html',user=user,oauth_providers=providers,can_mint_profile_token=True,
            account_display_email=lambda u:u.email or u.contact_email,account_mailbox_verified=lambda u:False)
        (out/f'profile-{kind}.html').write_text(html)
print('Rendered synthetic login and profile previews')
