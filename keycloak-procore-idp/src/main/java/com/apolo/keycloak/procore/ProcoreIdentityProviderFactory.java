package com.apolo.keycloak.procore;

import java.util.List;

import org.keycloak.broker.provider.AbstractIdentityProviderFactory;
import org.keycloak.models.IdentityProviderModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.provider.ProviderConfigProperty;

public final class ProcoreIdentityProviderFactory extends AbstractIdentityProviderFactory<ProcoreIdentityProvider> {

    public static final String PROVIDER_ID = ProcoreIdentityProviderConfig.PROVIDER_ID;

    private static final List<ProviderConfigProperty> CONFIG_PROPERTIES = List.of(
            new ProviderConfigProperty(
                    "clientId",
                    "Client ID",
                    "Procore OAuth2 client identifier registered for Keycloak.",
                    ProviderConfigProperty.STRING_TYPE,
                    null,
                    false),
            new ProviderConfigProperty(
                    "clientSecret",
                    "Client Secret",
                    "Procore OAuth2 client secret used only by the Keycloak server.",
                    ProviderConfigProperty.PASSWORD,
                    null,
                    true),
            new ProviderConfigProperty(
                    "authorizationUrl",
                    "Authorization URL",
                    "Procore OAuth2 authorization endpoint.",
                    ProviderConfigProperty.STRING_TYPE,
                    ProcoreIdentityProviderConfig.DEFAULT_AUTHORIZATION_URL,
                    false),
            new ProviderConfigProperty(
                    "tokenUrl",
                    "Token URL",
                    "Procore OAuth2 token endpoint.",
                    ProviderConfigProperty.STRING_TYPE,
                    ProcoreIdentityProviderConfig.DEFAULT_TOKEN_URL,
                    false),
            new ProviderConfigProperty(
                    ProcoreIdentityProviderConfig.ME_URL,
                    "/me URL",
                    "Procore user profile endpoint used to resolve the authenticated user.",
                    ProviderConfigProperty.STRING_TYPE,
                    ProcoreIdentityProviderConfig.DEFAULT_ME_URL,
                    false),
            new ProviderConfigProperty(
                    "defaultScope",
                    "Default Scope",
                    "Optional Procore scopes. Leave blank unless your Procore app requires specific scopes.",
                    ProviderConfigProperty.STRING_TYPE,
                    "",
                    false));

    @Override
    public ProcoreIdentityProvider create(KeycloakSession session, IdentityProviderModel model) {
        return new ProcoreIdentityProvider(session, new ProcoreIdentityProviderConfig(model));
    }

    @Override
    public ProcoreIdentityProviderConfig createConfig() {
        return new ProcoreIdentityProviderConfig();
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        return CONFIG_PROPERTIES;
    }

    @Override
    public String getHelpText() {
        return "Brokers users from Procore OAuth2 into local Keycloak accounts without exposing Procore tokens to frontend clients.";
    }

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

    @Override
    public String getName() {
        return "Procore";
    }
}
