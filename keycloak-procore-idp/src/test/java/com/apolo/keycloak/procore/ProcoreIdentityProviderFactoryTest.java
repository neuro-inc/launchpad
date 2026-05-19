package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;
import org.keycloak.models.IdentityProviderModel;
import org.keycloak.provider.ProviderConfigProperty;

class ProcoreIdentityProviderFactoryTest {

    @Test
    void exposesExpectedMetadata() {
        ProcoreIdentityProviderFactory factory = new ProcoreIdentityProviderFactory();

        assertEquals("procore", factory.getId());
        assertEquals("Procore", factory.getName());
        assertTrue(factory.getHelpText().contains("Procore OAuth2"));
    }

    @Test
    void createsDefaultConfig() {
        ProcoreIdentityProviderFactory factory = new ProcoreIdentityProviderFactory();

        ProcoreIdentityProviderConfig config = factory.createConfig();

        assertNotNull(config);
        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_AUTHORIZATION_URL, config.getAuthorizationUrl());
        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_TOKEN_URL, config.getTokenUrl());
        assertEquals(ProcoreIdentityProviderConfig.DEFAULT_ME_URL, config.getMeUrl());
    }

    @Test
    void returnsExpectedAdminConsoleProperties() {
        ProcoreIdentityProviderFactory factory = new ProcoreIdentityProviderFactory();

        List<ProviderConfigProperty> properties = factory.getConfigProperties();

        assertEquals(6, properties.size());
        assertEquals("clientId", properties.get(0).getName());
        assertEquals("clientSecret", properties.get(1).getName());
        assertEquals("authorizationUrl", properties.get(2).getName());
        assertEquals("tokenUrl", properties.get(3).getName());
        assertEquals(ProcoreIdentityProviderConfig.ME_URL, properties.get(4).getName());
        assertEquals("defaultScope", properties.get(5).getName());
    }

    @Test
    void createsProviderFromModel() {
        ProcoreIdentityProviderFactory factory = new ProcoreIdentityProviderFactory();
        IdentityProviderModel model = new IdentityProviderModel();
        model.setAlias("procore");
        model.setEnabled(true);
        model.getConfig().put("clientId", "client-id");
        model.getConfig().put("clientSecret", "client-secret");
        model.getConfig().put("authorizationUrl", ProcoreIdentityProviderConfig.DEFAULT_AUTHORIZATION_URL);
        model.getConfig().put("tokenUrl", ProcoreIdentityProviderConfig.DEFAULT_TOKEN_URL);
        model.getConfig().put(ProcoreIdentityProviderConfig.ME_URL, ProcoreIdentityProviderConfig.DEFAULT_ME_URL);

        ProcoreIdentityProvider provider = factory.create(null, model);

        assertInstanceOf(ProcoreIdentityProvider.class, provider);
        assertEquals("procore", provider.getConfig().getAlias());
        assertEquals("client-id", provider.getConfig().getClientId());
    }
}
