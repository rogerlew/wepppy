# CILogon email trust research

Research requested by the operator during the account-security checkpoint. This is evidence and a recommendation, not approval of a new trust policy.

## Findings

[CILogon OIDC guidance](https://www.cilogon.org/oidc) says some upstream providers do not supply stable or verified email and identifies issuer plus subject as the stable user key. Its live discovery advertises email but not email_verified. [CILogon's FAQ](https://www.cilogon.org/faq) explains that campus attributes are translated from SAML assertions into OIDC tokens. A validated CILogon response authenticates that assertion; it does not establish a uniform mailbox-verification policy across all upstream providers.

[JupyterHub advisory CVE-2022-31027](https://github.com/jupyterhub/oauthenticator/security/advisories/GHSA-r7v4-jwx9-wx43) concerns CILogon authorization based only on returned email domains. Its fix selects allowed upstream IdP EntityIDs. The advisory identifies the cross-provider impersonation risk if a provider permits unverified email, but explicitly states that the authors had not found such a provider at publication in June 2022. Do not report it as a demonstrated arbitrary-email exploit against CILogon itself. It also distinguishes historic email verification from current institutional membership.

[InCommon deployment guidance, June 7 2024, pages 17–18](https://spaces.at.internet2.edu/download/attachments/303104928/inc-refeds-access-ec-deployment-guide-20240607.pdf?api=v2&modificationDate=1717784857048&version=1) explains that institutional emails may change, be reassigned or shared, and may be user-supplied contact addresses without proof of mailbox control. Membership in a federation alone is not a blanket email-ownership guarantee.

[OAuthenticator's CILogon configuration](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.cilogon.html) supports per-IdP username derivation and authorization rules. Its current setup requires an explicit IdP configuration. This is precedent for bounded provider trust, not evidence that every configured provider verifies every email attribute.

## Recommendation for WEPPcloud

Keep stable issuer/subject binding after the initial link. For automatic first-link matching without a WEPPcloud email challenge, establish and document the upstream provider's email issuance/verification policy and the exact claim/domain scope it is authoritative for. Validate the returned upstream IdP identity on the server; do not rely on a picker hint or email suffix alone. Do not substitute eppn, MFA, or a generic assurance label for proof of ownership of the exact email without a documented claim-specific guarantee.

An IdP-specific policy would require CILogon's `org.cilogon.userinfo` scope to request its documented `idp` claim, expanding the original registration scope. Requesting a scope does not itself create assurance. Confirm registration changes before depending on it.

For unrestricted CILogon providers, prefer an existing-account authentication or a one-time mailbox challenge before linking an unmatched CILogon identity to existing data. A mailbox challenge establishes current control, not historic ownership; address recycling remains a limitation shared with email-based account recovery. Do not keep rematching email after the stable identity has been linked.

The exact upstream trust list and uncertain-assertion policy remain operator decisions. No blanket demand for repeated email verification on ordinary linked logins is justified by this research. The local-registration/password protection is a separate boundary and remains in scope.
