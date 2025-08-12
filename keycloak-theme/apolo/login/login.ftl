<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=social.providers??; section>
  <#if section = "header">
    Welcome
  <#elseif section = "form">
    <div class="kc-tagline">Login to Apolo Launchpad</div>
    <#-- Render the standard KC login form -->
    <#include "login-form.ftl">
  </#if>
</@layout.registrationLayout>
