package com.apolo.keycloak.procore;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;

public record ProcoreUserProfile(String id, String login, String name) {

    public static ProcoreUserProfile fromJson(JsonNode json) {
        if (json == null || json.isNull()) {
            throw new IllegalArgumentException("Profile response body is empty.");
        }

        String id = readRequiredField(json, "id");
        String login = readRequiredField(json, "login");
        String name = readOptionalField(json, "name");

        return new ProcoreUserProfile(id, login, name);
    }

    public ObjectNode toMapperJson() {
        ObjectNode node = JsonNodeFactory.instance.objectNode();
        node.put("id", id);
        node.put("login", login);
        if (name != null) {
            node.put("name", name);
        } else {
            node.putNull("name");
        }
        return node;
    }

    private static String readRequiredField(JsonNode json, String fieldName) {
        String value = readOptionalField(json, fieldName);
        if (!ProcoreIdentityProviderConfig.hasText(value)) {
            throw new IllegalArgumentException("Profile response does not contain a usable " + fieldName + " field.");
        }
        return value;
    }

    private static String readOptionalField(JsonNode json, String fieldName) {
        JsonNode value = json.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return ProcoreIdentityProviderConfig.hasText(text) ? text.trim() : null;
    }
}
