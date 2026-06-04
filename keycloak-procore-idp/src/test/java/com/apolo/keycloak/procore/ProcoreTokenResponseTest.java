package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

class ProcoreTokenResponseTest {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Test
    void parsesFullTokenPayload() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("access_token", "access-token");
        json.put("token_type", "Bearer");
        json.put("expires_in", 3600);
        json.put("refresh_token", "refresh-token");
        json.put("scope", "read write");

        ProcoreTokenResponse response = ProcoreTokenResponse.fromJson(json);

        assertEquals("access-token", response.accessToken());
        assertEquals("Bearer", response.tokenType());
        assertEquals(3600L, response.expiresIn());
        assertEquals("refresh-token", response.refreshToken());
        assertEquals("read write", response.scope());
    }

    @Test
    void trimsOptionalStringFields() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("access_token", " token ");
        json.put("token_type", " Bearer ");
        json.put("scope", " profile ");

        ProcoreTokenResponse response = ProcoreTokenResponse.fromJson(json);

        assertEquals("token", response.accessToken());
        assertEquals("Bearer", response.tokenType());
        assertEquals("profile", response.scope());
        assertNull(response.expiresIn());
        assertNull(response.refreshToken());
    }

    @Test
    void rejectsEmptyPayload() {
        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, () -> ProcoreTokenResponse.fromJson(null));

        assertEquals("Token response body is empty.", error.getMessage());
    }

    @Test
    void rejectsMissingAccessToken() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("token_type", "Bearer");

        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, () -> ProcoreTokenResponse.fromJson(json));

        assertEquals("Token response does not contain access_token.", error.getMessage());
    }

    @Test
    void ignoresNonNumericExpiresIn() throws Exception {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("access_token", "access-token");
        json.set("expires_in", OBJECT_MAPPER.readTree("\"3600\""));

        ProcoreTokenResponse response = ProcoreTokenResponse.fromJson(json);

        assertNull(response.expiresIn());
    }
}
