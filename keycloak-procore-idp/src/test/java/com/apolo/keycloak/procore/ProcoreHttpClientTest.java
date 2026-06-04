package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

class ProcoreHttpClientTest {

    @Test
    void exchangesAuthorizationCodeSuccessfully() {
        RecordingTransport transport = new RecordingTransport();
        transport.tokenResult = new ProcoreHttpClient.HttpResult(200, tokenJson("access-token"));
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        ProcoreTokenResponse response = client.exchangeAuthorizationCode("auth-code", "https://example/callback");

        assertEquals("auth-code", transport.authorizationCode);
        assertEquals("https://example/callback", transport.redirectUri);
        assertEquals("access-token", response.accessToken());
    }

    @Test
    void failsSafelyOnTokenExchangeErrorStatus() {
        RecordingTransport transport = new RecordingTransport();
        transport.tokenResult = new ProcoreHttpClient.HttpResult(401, errorJson("invalid_grant", null));
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> client.exchangeAuthorizationCode("auth-code", "https://example/callback"));

        assertEquals("Procore token exchange failed with status 401.", error.getMessage());
    }

    @Test
    void wrapsTokenExchangeIoFailure() {
        RecordingTransport transport = new RecordingTransport();
        transport.tokenException = new IOException("network");
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> client.exchangeAuthorizationCode("auth-code", "https://example/callback"));

        assertEquals("Unable to exchange Procore authorization code.", error.getMessage());
    }

    @Test
    void fetchesUserProfileSuccessfully() {
        RecordingTransport transport = new RecordingTransport();
        transport.profileResult = new ProcoreHttpClient.HttpResult(200, profileJson("15464862", "vt781309@gmail.com", "Jane Doe"));
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        ProcoreUserProfile profile = client.fetchUserProfile("access-token");

        assertEquals("access-token", transport.accessToken);
        assertEquals("15464862", profile.id());
        assertEquals("vt781309@gmail.com", profile.login());
        assertEquals("Jane Doe", profile.name());
    }

    @Test
    void failsSafelyOnProfileErrorStatus() {
        RecordingTransport transport = new RecordingTransport();
        transport.profileResult = new ProcoreHttpClient.HttpResult(500, errorJson(null, "server_error"));
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        IllegalStateException error =
                assertThrows(IllegalStateException.class, () -> client.fetchUserProfile("access-token"));

        assertEquals("Procore profile request failed with status 500.", error.getMessage());
    }

    @Test
    void wrapsProfileIoFailure() {
        RecordingTransport transport = new RecordingTransport();
        transport.profileException = new IOException("network");
        ProcoreHttpClient client = new ProcoreHttpClient(null, newConfig(), transport);

        IllegalStateException error =
                assertThrows(IllegalStateException.class, () -> client.fetchUserProfile("access-token"));

        assertEquals("Unable to fetch Procore user profile.", error.getMessage());
    }

    @Test
    void exposesSanitizedLogSummaryWithoutSecrets() {
        ProcoreIdentityProviderConfig config = newConfig();
        ProcoreHttpClient client = new ProcoreHttpClient(null, config, new RecordingTransport());

        Map<String, String> summary = client.sanitizeForLogSummary();

        assertEquals(config.getAuthorizationUrl(), summary.get("authorizationUrl"));
        assertEquals(config.getTokenUrl(), summary.get("tokenUrl"));
        assertEquals(config.getMeUrl(), summary.get("meUrl"));
        assertEquals("true", summary.get("clientIdConfigured"));
    }

    private static ProcoreIdentityProviderConfig newConfig() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();
        config.setClientId("client-id");
        config.setClientSecret("client-secret");
        config.setAuthorizationUrl("https://login.procore.example/oauth/authorize");
        config.setTokenUrl("https://login.procore.example/oauth/token");
        config.setMeUrl("https://api.procore.example/rest/v1.0/me");
        return config;
    }

    private static ObjectNode tokenJson(String accessToken) {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("access_token", accessToken);
        json.put("token_type", "Bearer");
        json.put("expires_in", 3600);
        return json;
    }

    private static ObjectNode profileJson(String id, String login, String name) {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("id", id);
        json.put("login", login);
        json.put("name", name);
        return json;
    }

    private static ObjectNode errorJson(String error, String errorDescription) {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        if (error != null) {
            json.put("error", error);
        }
        if (errorDescription != null) {
            json.put("error_description", errorDescription);
        }
        return json;
    }

    private static final class RecordingTransport implements ProcoreHttpClient.Transport {
        private ProcoreHttpClient.HttpResult tokenResult;
        private ProcoreHttpClient.HttpResult profileResult;
        private IOException tokenException;
        private IOException profileException;
        private String authorizationCode;
        private String redirectUri;
        private String accessToken;

        @Override
        public ProcoreHttpClient.HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException {
            this.authorizationCode = authorizationCode;
            this.redirectUri = redirectUri;
            if (tokenException != null) {
                throw tokenException;
            }
            return tokenResult;
        }

        @Override
        public ProcoreHttpClient.HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken)
                throws IOException {
            this.accessToken = accessToken;
            if (profileException != null) {
                throw profileException;
            }
            return profileResult;
        }
    }
}
