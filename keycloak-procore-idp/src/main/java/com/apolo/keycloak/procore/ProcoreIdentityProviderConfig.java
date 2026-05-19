package com.apolo.keycloak.procore;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

import org.keycloak.broker.oidc.OAuth2IdentityProviderConfig;
import org.keycloak.models.IdentityProviderModel;

public final class ProcoreIdentityProviderConfig extends OAuth2IdentityProviderConfig {

    public static final String PROVIDER_ID = "procore";
    public static final String ME_URL = "meUrl";
    public static final String CLIENT_SECRET_POST = "client_secret_post";
    public static final String DEFAULT_AUTHORIZATION_URL = "https://login.procore.com/oauth/authorize";
    public static final String DEFAULT_TOKEN_URL = "https://login.procore.com/oauth/token";
    public static final String DEFAULT_ME_URL = "https://api.procore.com/rest/v1.0/me";

    public ProcoreIdentityProviderConfig() {
        applyDefaults();
    }

    public ProcoreIdentityProviderConfig(IdentityProviderModel model) {
        super(model);
        applyDefaults();
    }

    public String getMeUrl() {
        String configured = getConfig().get(ME_URL);
        return hasText(configured) ? configured : DEFAULT_ME_URL;
    }

    public void setMeUrl(String meUrl) {
        getConfig().put(ME_URL, meUrl);
    }

    public void applyDefaults() {
        if (!hasText(getAuthorizationUrl())) {
            setAuthorizationUrl(DEFAULT_AUTHORIZATION_URL);
        }
        if (!hasText(getTokenUrl())) {
            setTokenUrl(DEFAULT_TOKEN_URL);
        }
        if (!hasText(getMeUrl())) {
            setMeUrl(DEFAULT_ME_URL);
        }
        if (!hasText(getClientAuthMethod())) {
            setClientAuthMethod(CLIENT_SECRET_POST);
        }
        if (getDefaultScope() == null) {
            setDefaultScope("");
        }
        setStoreToken(false);
        setStoreTokenInSession(false);
        setPkceEnabled(false);
    }

    public void validateProviderConfiguration() {
        validateRequired("clientId", getClientId());
        validateRequired("clientSecret", getClientSecret());
        validateHttpsUrl("authorizationUrl", getAuthorizationUrl());
        validateHttpsUrl("tokenUrl", getTokenUrl());
        validateHttpsUrl(ME_URL, getMeUrl());
    }

    private static void validateRequired(String fieldName, String value) {
        if (!hasText(value)) {
            throw new IllegalArgumentException("Missing required Procore provider setting: " + fieldName);
        }
    }

    private static void validateHttpsUrl(String fieldName, String value) {
        if (!hasText(value)) {
            throw new IllegalArgumentException("Missing required Procore provider URL: " + fieldName);
        }
        try {
            URI uri = new URI(value);
            String scheme = uri.getScheme();
            if (!hasText(scheme) || !"https".equals(scheme.toLowerCase(Locale.ROOT))) {
                throw new IllegalArgumentException("Procore provider URL must use https: " + fieldName);
            }
            if (!hasText(uri.getHost())) {
                throw new IllegalArgumentException("Procore provider URL must include a host: " + fieldName);
            }
        } catch (URISyntaxException exception) {
            throw new IllegalArgumentException("Invalid Procore provider URL: " + fieldName, exception);
        }
    }

    static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
