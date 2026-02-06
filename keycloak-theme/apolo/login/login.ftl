<#import "template.ftl" as layout>
<#import "field.ftl" as field>
<#import "buttons.ftl" as buttons>
<#import "social-providers.ftl" as identityProviders>
<#import "passkeys.ftl" as passkeys>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
<!-- template: login.ftl -->

    <#if section = "head">
        <#-- Inject custom background color from environment variable if available -->
        <#if properties.brandingBackgroundColor?has_content>
        <style>
            body,
            .pf-c-login,
            .pf-v5-c-login {
                background-color: ${properties.brandingBackgroundColor} !important;
            }
        </style>
        </#if>
    <#elseif section = "header">
        <#-- Try to use custom logo first, fallback to default -->
        <#assign customLogo = "${url.resourcesPath}/branding/logo">
        <#assign defaultLogo = "${url.resourcesPath}/img/launchpad-logo.svg">
        <img src="${customLogo}" alt="Launchpad" class="kc-logo" onerror="this.onerror=null; this.src='${defaultLogo}';" />
    <#elseif section = "form">
        <div id="kc-form">
          <div id="kc-form-wrapper">
            <#if realm.password>
                <form id="kc-form-login" class="${properties.kcFormClass!}" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post" novalidate="novalidate">
                    <#if !usernameHidden??>
                        <#assign label>
                            <#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>
                        </#assign>
                        <@field.input name="username" label=label error=kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc
                            autofocus=true autocomplete="${(enableWebAuthnConditionalUI?has_content)?then('username webauthn', 'username')}" value=login.username!'' />
                        <@field.password name="password" label=msg("password") error=kcSanitize(messagesPerField.getFirstError('password'))?no_esc forgotPassword=false autofocus=usernameHidden?? autocomplete="current-password">
                        </@field.password>
                    <#else>
                        <@field.password name="password" label=msg("password") error=kcSanitize(messagesPerField.getFirstError('password'))?no_esc forgotPassword=false autofocus=usernameHidden?? autocomplete="current-password">
                        </@field.password>
                    </#if>

                    <input type="hidden" id="id-hidden-input" name="credentialId" <#if auth.selectedCredential?has_content>value="${auth.selectedCredential}"</#if>/>
                    <@buttons.loginButton />
                </form>
            </#if>
            </div>
        </div>
        <@passkeys.conditionalUIData />
    <#elseif section = "socialProviders" >
        <#if realm.password && social.providers?? && social.providers?has_content>
            <@identityProviders.show social=social/>
        </#if>
    <#elseif section = "info" >
        <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
            <div id="kc-registration-container">
                <div id="kc-registration">
                    <span>${msg("noAccount")} <a href="${url.registrationUrl}">${msg("doRegister")}</a></span>
                </div>
            </div>
        </#if>
    </#if>

</@layout.registrationLayout>
