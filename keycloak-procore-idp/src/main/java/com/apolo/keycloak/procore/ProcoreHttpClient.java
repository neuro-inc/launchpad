package com.apolo.keycloak.procore;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import jakarta.ws.rs.core.Response;
import org.apache.http.client.config.RequestConfig;
import org.jboss.logging.Logger;
import org.keycloak.http.simple.SimpleHttp;
import org.keycloak.http.simple.SimpleHttpRequest;
import org.keycloak.http.simple.SimpleHttpResponse;
import org.keycloak.models.KeycloakSession;

import com.fasterxml.jackson.databind.JsonNode;

public final class ProcoreHttpClient {

    private static final Logger LOG = Logger.getLogger(ProcoreHttpClient.class);
    private static final int CONNECT_TIMEOUT_MILLIS = 5_000;
    private static final int CONNECTION_REQUEST_TIMEOUT_MILLIS = 5_000;
    private static final int SOCKET_TIMEOUT_MILLIS = 10_000;
    private static final long MAX_RESPONSE_SIZE_BYTES = 1_048_576L;

    private final KeycloakSession session;
    private final ProcoreIdentityProviderConfig config;
    private final RequestConfig requestConfig;
    private final Transport transport;

    public ProcoreHttpClient(KeycloakSession session, ProcoreIdentityProviderConfig config) {
        this(session, config, null);
    }

    ProcoreHttpClient(KeycloakSession session, ProcoreIdentityProviderConfig config, Transport transport) {
        this.session = session;
        this.config = config;
        this.requestConfig = RequestConfig.custom()
                .setConnectTimeout(CONNECT_TIMEOUT_MILLIS)
                .setConnectionRequestTimeout(CONNECTION_REQUEST_TIMEOUT_MILLIS)
                .setSocketTimeout(SOCKET_TIMEOUT_MILLIS)
                .build();
        this.transport = transport != null ? transport : new SimpleHttpTransport();
    }

    public ProcoreTokenResponse exchangeAuthorizationCode(String authorizationCode, String redirectUri) {
        try {
            return parseTokenResponse(transport.exchangeAuthorizationCode(config, authorizationCode, redirectUri));
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to exchange Procore authorization code.", exception);
        }
    }

    public ProcoreUserProfile fetchUserProfile(String accessToken) {
        try {
            HttpResult response = transport.fetchUserProfile(config, accessToken);
            int status = response.status();
            JsonNode body = response.body();
            if (!isSuccessful(status)) {
                String errorCode = readErrorCode(body);
                LOG.warnf("Procore profile request failed with status=%d error=%s", status, errorCode);
                throw new IllegalStateException("Procore profile request failed with status " + status + ".");
            }
            return ProcoreUserProfile.fromJson(body);
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to fetch Procore user profile.", exception);
        }
    }

    private ProcoreTokenResponse parseTokenResponse(HttpResult response) {
        int status = response.status();
        JsonNode body = response.body();
        if (!isSuccessful(status)) {
            String errorCode = readErrorCode(body);
            LOG.warnf("Procore token exchange failed with status=%d error=%s", status, errorCode);
            throw new IllegalStateException("Procore token exchange failed with status " + status + ".");
        }
        return ProcoreTokenResponse.fromJson(body);
    }

    private SimpleHttp http() {
        return SimpleHttp.create(session)
                .withRequestConfig(requestConfig)
                .withMaxConsumedResponseSize(MAX_RESPONSE_SIZE_BYTES);
    }

    private static String readErrorCode(JsonNode body) {
        if (body == null || body.isNull()) {
            return "unknown";
        }
        String error = readText(body, "error");
        if (ProcoreIdentityProviderConfig.hasText(error)) {
            return error;
        }
        String errorDescription = readText(body, "error_description");
        if (ProcoreIdentityProviderConfig.hasText(errorDescription)) {
            return errorDescription;
        }
        return "unknown";
    }

    private static String readText(JsonNode body, String fieldName) {
        JsonNode value = body.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return ProcoreIdentityProviderConfig.hasText(text) ? text.trim() : null;
    }

    private static boolean isSuccessful(int status) {
        return Response.Status.Family.familyOf(status) == Response.Status.Family.SUCCESSFUL;
    }

    public Map<String, String> sanitizeForLogSummary() {
        Map<String, String> summary = new LinkedHashMap<>();
        summary.put("authorizationUrl", config.getAuthorizationUrl());
        summary.put("tokenUrl", config.getTokenUrl());
        summary.put("meUrl", config.getMeUrl());
        summary.put("clientIdConfigured", Boolean.toString(ProcoreIdentityProviderConfig.hasText(config.getClientId())));
        return summary;
    }

    interface Transport {
        HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException;

        HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken) throws IOException;
    }

    record HttpResult(int status, JsonNode body) {
    }

    private final class SimpleHttpTransport implements Transport {

        @Override
        public HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException {
            SimpleHttpRequest request = http().doPost(config.getTokenUrl())
                    .param("grant_type", "authorization_code")
                    .param("code", authorizationCode)
                    .param("redirect_uri", redirectUri)
                    .param("client_id", config.getClientId())
                    .acceptJson();

            if (config.isBasicAuthentication()) {
                request.authBasic(config.getClientId(), config.getClientSecret());
            } else {
                request.param("client_secret", config.getClientSecret());
            }

            try (SimpleHttpResponse response = request.asResponse()) {
                return new HttpResult(response.getStatus(), response.asJson());
            }
        }

        @Override
        public HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken) throws IOException {
            try (SimpleHttpResponse response = http().doGet(config.getMeUrl())
                    .header("Authorization", "Bearer " + accessToken)
                    .acceptJson()
                    .asResponse()) {
                return new HttpResult(response.getStatus(), response.asJson());
            }
        }
    }
}
