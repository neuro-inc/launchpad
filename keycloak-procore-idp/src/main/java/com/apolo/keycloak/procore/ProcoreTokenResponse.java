package com.apolo.keycloak.procore;

import com.fasterxml.jackson.databind.JsonNode;

public record ProcoreTokenResponse(
        String accessToken,
        String tokenType,
        Long expiresIn,
        String refreshToken,
        String scope) {

    public static ProcoreTokenResponse fromJson(JsonNode json) {
        if (json == null || json.isNull()) {
            throw new IllegalArgumentException("Token response body is empty.");
        }

        String accessToken = textValue(json, "access_token");
        if (!ProcoreIdentityProviderConfig.hasText(accessToken)) {
            throw new IllegalArgumentException("Token response does not contain access_token.");
        }

        return new ProcoreTokenResponse(
                accessToken,
                textValue(json, "token_type"),
                longValue(json, "expires_in"),
                textValue(json, "refresh_token"),
                textValue(json, "scope"));
    }

    private static String textValue(JsonNode json, String fieldName) {
        JsonNode value = json.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return ProcoreIdentityProviderConfig.hasText(text) ? text.trim() : null;
    }

    private static Long longValue(JsonNode json, String fieldName) {
        JsonNode value = json.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        return value.isNumber() ? value.longValue() : null;
    }
}
