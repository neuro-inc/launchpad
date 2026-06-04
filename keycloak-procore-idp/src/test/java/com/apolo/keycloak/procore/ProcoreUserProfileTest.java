package com.apolo.keycloak.procore;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

class ProcoreUserProfileTest {

    @Test
    void parsesAndNormalizesProfile() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("id", 15464862);
        json.put("login", " vt781309@gmail.com ");
        json.put("name", " Jane Doe ");

        ProcoreUserProfile profile = ProcoreUserProfile.fromJson(json);

        assertEquals("15464862", profile.id());
        assertEquals("vt781309@gmail.com", profile.login());
        assertEquals("Jane Doe", profile.name());
    }

    @Test
    void allowsMissingName() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("id", 15464862);
        json.put("login", "vt781309@gmail.com");

        ProcoreUserProfile profile = ProcoreUserProfile.fromJson(json);

        assertNull(profile.name());
        assertTrue(profile.toMapperJson().get("name").isNull());
    }

    @Test
    void rejectsMissingId() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("login", "vt781309@gmail.com");

        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, () -> ProcoreUserProfile.fromJson(json));

        assertEquals("Profile response does not contain a usable id field.", error.getMessage());
    }

    @Test
    void rejectsBlankLogin() {
        ObjectNode json = JsonNodeFactory.instance.objectNode();
        json.put("id", 15464862);
        json.put("login", "   ");

        IllegalArgumentException error =
                assertThrows(IllegalArgumentException.class, () -> ProcoreUserProfile.fromJson(json));

        assertEquals("Profile response does not contain a usable login field.", error.getMessage());
    }

    @Test
    void mapperJsonContainsExpectedFields() {
        ProcoreUserProfile profile = new ProcoreUserProfile("15464862", "vt781309@gmail.com", "Jane Doe");

        ObjectNode mapperJson = profile.toMapperJson();

        assertEquals("15464862", mapperJson.get("id").asText());
        assertEquals("vt781309@gmail.com", mapperJson.get("login").asText());
        assertEquals("Jane Doe", mapperJson.get("name").asText());
    }
}
