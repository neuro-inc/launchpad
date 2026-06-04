package com.apolo.keycloak.procore;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.StringJoiner;

import jakarta.ws.rs.core.Response;
import org.jboss.logging.Logger;

import com.fasterxml.jackson.databind.JsonNode;

public final class ProcoreHttpClient {

    private static final Logger LOG = Logger.getLogger(ProcoreHttpClient.class);
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(5);
    private static final Duration READ_TIMEOUT = Duration.ofSeconds(10);

    private final ProcoreIdentityProviderConfig config;
    private final HttpClient httpClient;
    private final Transport transport;

    public ProcoreHttpClient(ProcoreIdentityProviderConfig config) {
        this(config, null, null);
    }

    ProcoreHttpClient(HttpClient httpClient, ProcoreIdentityProviderConfig config, Transport transport) {
        this(config, httpClient, transport);
    }

    ProcoreHttpClient(ProcoreIdentityProviderConfig config, HttpClient httpClient, Transport transport) {
        this.config = config;
        this.httpClient = httpClient != null ? httpClient : HttpClient.newBuilder()
                .connectTimeout(CONNECT_TIMEOUT)
                .build();
        this.transport = transport != null ? transport : new JavaNetTransport();
    }

    public ProcoreTokenResponse exchangeAuthorizationCode(String authorizationCode, String redirectUri) {
        try {
            return parseTokenResponse(transport.exchangeAuthorizationCode(config, authorizationCode, redirectUri));
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Unable to exchange Procore authorization code.", exception);
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
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Unable to fetch Procore user profile.", exception);
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

    private static String formEncode(Map<String, String> params) {
        StringJoiner sj = new StringJoiner("&");
        for (Map.Entry<String, String> entry : params.entrySet()) {
            sj.add(URLEncoder.encode(entry.getKey(), StandardCharsets.UTF_8)
                    + "=" + URLEncoder.encode(entry.getValue(), StandardCharsets.UTF_8));
        }
        return sj.toString();
    }

    private static JsonNode parseJson(HttpResponse<byte[]> response) throws IOException {
        byte[] body = response.body();
        if (body == null || body.length == 0) {
            return null;
        }
        return ProcoreUserProfile.MAPPER.readTree(body);
    }

    interface Transport {
        HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException, InterruptedException;

        HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken) throws IOException, InterruptedException;
    }

    record HttpResult(int status, JsonNode body) {
    }

    private final class JavaNetTransport implements Transport {

        @Override
        public HttpResult exchangeAuthorizationCode(
                ProcoreIdentityProviderConfig config,
                String authorizationCode,
                String redirectUri) throws IOException, InterruptedException {
            Map<String, String> params = new LinkedHashMap<>();
            params.put("grant_type", "authorization_code");
            params.put("code", authorizationCode);
            params.put("redirect_uri", redirectUri);
            params.put("client_id", config.getClientId());

            if (config.isBasicAuthentication()) {
                String creds = config.getClientId() + ":" + config.getClientSecret();
                String auth = java.util.Base64.getEncoder().encodeToString(creds.getBytes(StandardCharsets.UTF_8));
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(config.getTokenUrl()))
                        .timeout(READ_TIMEOUT)
                        .header("Content-Type", "application/x-www-form-urlencoded")
                        .header("Authorization", "Basic " + auth)
                        .POST(HttpRequest.BodyPublishers.ofString(formEncode(params)))
                        .build();
                HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
                return new HttpResult(response.statusCode(), parseJson(response));
            } else {
                params.put("client_secret", config.getClientSecret());
                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(config.getTokenUrl()))
                        .timeout(READ_TIMEOUT)
                        .header("Content-Type", "application/x-www-form-urlencoded")
                        .POST(HttpRequest.BodyPublishers.ofString(formEncode(params)))
                        .build();
                HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
                return new HttpResult(response.statusCode(), parseJson(response));
            }
        }

        @Override
        public HttpResult fetchUserProfile(ProcoreIdentityProviderConfig config, String accessToken) throws IOException, InterruptedException {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(config.getMeUrl()))
                    .timeout(READ_TIMEOUT)
                    .header("Authorization", "Bearer " + accessToken)
                    .header("Accept", "application/json")
                    .GET()
                    .build();
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            return new HttpResult(response.statusCode(), parseJson(response));
        }
    }
}
