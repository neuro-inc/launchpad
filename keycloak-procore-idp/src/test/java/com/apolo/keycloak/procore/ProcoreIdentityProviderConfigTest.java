package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class ProcoreIdentityProviderConfigTest {

    @Test
    void appliesSecureDefaults() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();

        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_AUTHORIZATION_URL, config.getAuthorizationUrl());
        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_TOKEN_URL, config.getTokenUrl());
        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_ME_URL, config.getMeUrl());
        assertEquals(ProcoreIdentityProviderConfig.CLIENT_SECRET_POST, config.getClientAuthMethod());
        assertEquals("", config.getDefaultScope());
        assertFalse(config.isStoreToken());
        assertFalse(config.isPkceEnabled());
    }

    @Test
    void validatesConfiguredHttpsEndpoints() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();
        config.setClientId("client-id");
        config.setClientSecret("client-secret");
        config.setAuthorizationUrl("https://login.procore.example/oauth/authorize");
        config.setTokenUrl("https://login.procore.example/oauth/token");
        config.setMeUrl("https://api.procore.example/rest/v1.0/me");

        config.validateProviderConfiguration();
    }

    @Test
    void rejectsMissingClientId() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();
        config.setClientSecret("client-secret");

        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, config::validateProviderConfiguration);

        assertTrue(error.getMessage().contains("clientId"));
    }

    @Test
    void rejectsNonHttpsUrls() {
        ProcoreIdentityProviderConfig config = new ProcoreIdentityProviderConfig();
        config.setClientId("client-id");
        config.setClientSecret("client-secret");
        config.setAuthorizationUrl("http://login.procore.example/oauth/authorize");

        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, config::validateProviderConfiguration);

        assertTrue(error.getMessage().contains("https"));
    }

    @Test
    void hasTextMatchesExpectedSemantics() {
        assertTrue(ProcoreIdentityProviderConfig.hasText("x"));
        assertFalse(ProcoreIdentityProviderConfig.hasText(""));
        assertFalse(ProcoreIdentityProviderConfig.hasText("   "));
        assertFalse(ProcoreIdentityProviderConfig.hasText(null));
    }
}
