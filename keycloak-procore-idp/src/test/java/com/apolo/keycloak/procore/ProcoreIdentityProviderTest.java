package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;

import org.junit.jupiter.api.Test;
import org.keycloak.broker.provider.BrokeredIdentityContext;
import org.keycloak.broker.provider.IdentityBrokerException;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

class ProcoreIdentityProviderTest {

    @Test
    void mapsProfileIntoBrokeredIdentityContext() {
        ProcoreIdentityProvider provider = newProvider();
        ObjectNode profile = JsonNodeFactory.instance.objectNode();
        profile.put("id", 15464862);
        profile.put("login", "vt781309@gmail.com");
        profile.put("name", "Jane Doe");

        BrokeredIdentityContext context = provider.extractIdentityFromProfile(null, profile);

        assertEquals("15464862", context.getId());
        assertEquals("15464862", context.getBrokerUserId());
        assertEquals("vt781309@gmail.com", context.getUsername());
        assertEquals("vt781309@gmail.com", context.getModelUsername());
        assertEquals("vt781309@gmail.com", context.getEmail());
        assertEquals("15464862", context.getUserAttribute("procore_user_id"));
        assertEquals("vt781309@gmail.com", context.getUserAttribute("procore_login"));
        assertEquals("procore", context.getUserAttribute("identity_source"));
        assertEquals("Jane", context.getFirstName());
        assertEquals("Doe", context.getLastName());
    }

    @Test
    void keepsSingleWordNameAsFirstNameOnly() {
        ProcoreIdentityProvider provider = newProvider();
        ObjectNode profile = JsonNodeFactory.instance.objectNode();
        profile.put("id", 15464862);
        profile.put("login", "vt781309@gmail.com");
        profile.put("name", "Prince");

        BrokeredIdentityContext context = provider.extractIdentityFromProfile(null, profile);

        assertEquals("Prince", context.getFirstName());
        assertNull(context.getLastName());
    }

    @Test
    void leavesNamesUnsetWhenProfileNameMissing() {
        ProcoreIdentityProvider provider = newProvider();
        ObjectNode profile = JsonNodeFactory.instance.objectNode();
        profile.put("id", 15464862);
        profile.put("login", "vt781309@gmail.com");

        BrokeredIdentityContext context = provider.extractIdentityFromProfile(null, profile);

        assertNull(context.getFirstName());
        assertNull(context.getLastName());
    }

    @Test
    void wrapsMalformedProfileAsIdentityBrokerException() {
        ProcoreIdentityProvider provider = newProvider();
        ObjectNode profile = JsonNodeFactory.instance.objectNode();
        profile.put("id", 15464862);

        IdentityBrokerException error =
                assertThrows(IdentityBrokerException.class, () -> provider.extractIdentityFromProfile(null, profile));

        assertEquals("Malformed Procore profile response.", error.getMessage());
    }

    @Test
    void doGetFederatedIdentityMapsFetchedProfile() {
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), new FixedTransport(
                null,
                null,
                new ProcoreHttpClient.HttpResult(200, profileJson("15464862", "vt781309@gmail.com", "Jane Doe")),
                null));
        ProcoreIdentityProvider provider = newProvider(client);

        BrokeredIdentityContext context = provider.doGetFederatedIdentity("access-token");

        assertEquals("15464862", context.getId());
        assertEquals("vt781309@gmail.com", context.getEmail());
        assertEquals("Jane", context.getFirstName());
        assertEquals("Doe", context.getLastName());
    }

    @Test
    void doGetFederatedIdentityWrapsUpstreamFailure() {
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), new FixedTransport(
                null,
                null,
                null,
                new IOException("boom")));
        ProcoreIdentityProvider provider = newProvider(client);

        IdentityBrokerException error =
                assertThrows(IdentityBrokerException.class, () -> provider.doGetFederatedIdentity("access-token"));

        assertEquals("Could not retrieve Procore user profile.", error.getMessage());
        assertInstanceOf(IllegalStateException.class, error.getCause());
    }

    @Test
    void defaultScopesAreEmpty() {
        ProcoreIdentityProvider provider = newProvider();

        assertEquals("", provider.getDefaultScopes());
    }

    private static ProcoreIdentityProvider newProvider() {
        return newProvider(null);
    }

    private static ProcoreIdentityProvider newProvider(ProcoreHttpClient client) {
        ProcoreIdentityProviderConfig config = newConfig();
        return new ProcoreIdentityProvider(null, config, client);
    }

    private static ProcoreIdentityProviderConfig newConfig() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();
        config.setAlias("procore");
        config.setEnabled(true);
        config.setClientId("client-id");
        config.setClientSecret("client-secret");
        return config;
    }

    private static ObjectNode profileJson(String id, String login, String name) {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("id", id);
        json.put("login", login);
        json.put("name", name);
        return json;
    }

    private record FixedTransport(
            ProcoreHttpClient.HttpResult tokenResult,
            IOException tokenException,
            ProcoreHttpClient.HttpResult profileResult,
            IOException profileException) implements ProcoreHttpClient.Transport {

        @Override
        public ProcoreHttpClient.HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException {
            if (tokenException != null) {
                throw tokenException;
            }
            return tokenResult;
        }

        @Override
        public ProcoreHttpClient.HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken)
                throws IOException {
            if (profileException != null) {
                throw profileException;
            }
            return profileResult;
        }
    }
}
