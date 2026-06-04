package com.apolo.keycloak.procore;

import org.jboss.logging.Logger;
import org.keycloak.broker.oidc.AbstractOAuth2IdentityProvider;
import org.keycloak.broker.oidc.mappers.AbstractJsonUserAttributeMapper;
import org.keycloak.broker.provider.BrokeredIdentityContext;
import org.keycloak.broker.provider.IdentityBrokerException;
import org.keycloak.events.EventBuilder;
import org.keycloak.models.KeycloakSession;

import com.fasterxml.jackson.databind.JsonNode;

public final class ProcoreIdentityProvider extends AbstractOAuth2IdentityProvider<ProcoreIdentityProviderConfig> {

    private static final Logger LOG = Logger.getLogger(ProcoreIdentityProvider.class);
    private static final String ATTRIBUTE_PROCORE_USER_ID = "procore_user_id";
    private static final String ATTRIBUTE_PROCORE_LOGIN = "procore_login";
    private static final String ATTRIBUTE_IDENTITY_SOURCE = "identity_source";

    private final ProcoreHttpClient httpClient;

    public ProcoreIdentityProvider(KeycloakSession session, ProcoreIdentityProviderConfig config) {
        this(session, config, null);
    }

    ProcoreIdentityProvider(KeycloakSession session, ProcoreIdentityProviderConfig config, ProcoreHttpClient httpClient) {
        super(session, config);
        config.applyDefaults();
        config.validateProviderConfiguration();
        this.httpClient = httpClient != null ? httpClient : new ProcoreHttpClient(config);
        LOG.debugf("Initialized Procore identity provider with config %s", this.httpClient.sanitizeForLogSummary());
    }

    @Override
    protected BrokeredIdentityContext doGetFederatedIdentity(String accessToken) {
        try {
            ProcoreUserProfile profile = httpClient.fetchUserProfile(accessToken);
            BrokeredIdentityContext identity = toBrokeredIdentityContext(profile);
            LOG.debugf("Resolved Procore identity for subject=%s login=%s", profile.id(), profile.login());
            return identity;
        } catch (RuntimeException exception) {
            LOG.warnf("Failed to retrieve Procore user profile: %s", exception.getMessage());
            throw new IdentityBrokerException("Could not retrieve Procore user profile.", exception);
        }
    }

    @Override
    protected BrokeredIdentityContext extractIdentityFromProfile(EventBuilder event, JsonNode profile) {
        try {
            return toBrokeredIdentityContext(ProcoreUserProfile.fromJson(profile));
        } catch (RuntimeException exception) {
            throw new IdentityBrokerException("Malformed Procore profile response.", exception);
        }
    }

    @Override
    protected String getDefaultScopes() {
        return "";
    }

    private BrokeredIdentityContext toBrokeredIdentityContext(ProcoreUserProfile profile) {
        BrokeredIdentityContext context = new BrokeredIdentityContext(profile.id(), getConfig());
        context.setIdp(this);
        context.setBrokerUserId(profile.id());
        context.setUsername(profile.login());
        context.setModelUsername(profile.login());
        context.setEmail(profile.login());
        context.setUserAttribute(ATTRIBUTE_PROCORE_USER_ID, profile.id());
        context.setUserAttribute(ATTRIBUTE_PROCORE_LOGIN, profile.login());
        context.setUserAttribute(ATTRIBUTE_IDENTITY_SOURCE, ProcoreIdentityProviderConfig.PROVIDER_ID);

        if (ProcoreIdentityProviderConfig.hasText(profile.name())) {
            NameParts nameParts = NameParts.from(profile.name());
            if (nameParts.firstName() != null) {
                context.setFirstName(nameParts.firstName());
            }
            if (nameParts.lastName() != null) {
                context.setLastName(nameParts.lastName());
            }
        }

        AbstractJsonUserAttributeMapper.storeUserProfileForMapper(context, profile.toMapperJson(), getConfig().getAlias());
        return context;
    }

    private record NameParts(String firstName, String lastName) {

        private static NameParts from(String fullName) {
            String normalized = fullName == null ? null : fullName.trim();
            if (!ProcoreIdentityProviderConfig.hasText(normalized)) {
                return new NameParts(null, null);
            }

            int separator = normalized.indexOf(' ');
            if (separator < 0) {
                return new NameParts(normalized, null);
            }

            String firstName = normalized.substring(0, separator).trim();
            String lastName = normalized.substring(separator + 1).trim();
            return new NameParts(
                    ProcoreIdentityProviderConfig.hasText(firstName) ? firstName : null,
                    ProcoreIdentityProviderConfig.hasText(lastName) ? lastName : null);
        }
    }
}
