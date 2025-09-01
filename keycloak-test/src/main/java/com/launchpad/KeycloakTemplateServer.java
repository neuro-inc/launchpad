package com.launchpad;

import freemarker.template.Configuration;
import freemarker.template.Template;
import freemarker.template.TemplateException;
import freemarker.template.TemplateExceptionHandler;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.*;
import java.net.InetSocketAddress;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Logger;

public class KeycloakTemplateServer {
    private static final Logger logger = Logger.getLogger(KeycloakTemplateServer.class.getName());
    private static final int PORT = 8080;
    private Configuration freemarkerConfig;

    public KeycloakTemplateServer() throws IOException {
        setupFreeMarker();
    }

    private void setupFreeMarker() throws IOException {
        freemarkerConfig = new Configuration(Configuration.VERSION_2_3_32);
        freemarkerConfig.setClassForTemplateLoading(this.getClass(), "/templates");
        freemarkerConfig.setDefaultEncoding("UTF-8");
        freemarkerConfig.setTemplateExceptionHandler(TemplateExceptionHandler.RETHROW_HANDLER);
        freemarkerConfig.setLogTemplateExceptions(false);
        freemarkerConfig.setWrapUncheckedExceptions(true);
        freemarkerConfig.setFallbackOnNullLoopVariable(false);
    }

    public void start() throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress(PORT), 0);
        
        // Serve the login page
        server.createContext("/login", new LoginHandler());
        
        // Serve the login page with errors for testing
        server.createContext("/login-error", new LoginErrorHandler());
        
        // Serve static resources (CSS, images, etc.)
        server.createContext("/resources", new StaticResourceHandler());
        
        // Redirect root to login
        server.createContext("/", new RootHandler());
        
        server.setExecutor(null);
        server.start();
        
        logger.info("Server started on http://localhost:" + PORT);
        logger.info("Open http://localhost:" + PORT + "/login to view the login page");
        logger.info("Open http://localhost:" + PORT + "/login-error to view the login page with errors");
    }

    private class LoginHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                Template template = freemarkerConfig.getTemplate("login.ftl");
                Map<String, Object> dataModel = createDataModel();
                
                StringWriter stringWriter = new StringWriter();
                template.process(dataModel, stringWriter);
                
                String response = stringWriter.toString();
                
                exchange.getResponseHeaders().set("Content-Type", "text/html; charset=UTF-8");
                exchange.sendResponseHeaders(200, response.getBytes("UTF-8").length);
                
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(response.getBytes("UTF-8"));
                }
                
            } catch (TemplateException e) {
                String errorResponse = "Template processing error: " + e.getMessage();
                exchange.sendResponseHeaders(500, errorResponse.length());
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(errorResponse.getBytes());
                }
                logger.severe("Template processing error: " + e.getMessage());
            }
        }
    }

    private class LoginErrorHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                Template template = freemarkerConfig.getTemplate("login.ftl");
                Map<String, Object> dataModel = createErrorDataModel();
                
                StringWriter stringWriter = new StringWriter();
                template.process(dataModel, stringWriter);
                
                String response = stringWriter.toString();
                
                exchange.getResponseHeaders().set("Content-Type", "text/html; charset=UTF-8");
                exchange.sendResponseHeaders(200, response.getBytes("UTF-8").length);
                
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(response.getBytes("UTF-8"));
                }
                
            } catch (TemplateException e) {
                String errorResponse = "Template processing error: " + e.getMessage();
                exchange.sendResponseHeaders(500, errorResponse.length());
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(errorResponse.getBytes());
                }
                logger.severe("Template processing error: " + e.getMessage());
            }
        }
    }

    private class StaticResourceHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            String response = "/* Static resources would be served here */";
            exchange.getResponseHeaders().set("Content-Type", "text/css");
            exchange.sendResponseHeaders(200, response.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(response.getBytes());
            }
        }
    }

    private class RootHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            exchange.getResponseHeaders().set("Location", "/login");
            exchange.sendResponseHeaders(302, -1);
        }
    }

    private Map<String, Object> createDataModel() {
        Map<String, Object> dataModel = new HashMap<>();
        
        // Basic template variables
        dataModel.put("title", "Login to Launchpad");
        dataModel.put("usernameLabel", "Username or Email");
        dataModel.put("passwordLabel", "Password");
        dataModel.put("loginButtonText", "Log In");
        dataModel.put("username", "");
        
        // Optional features - all disabled
        dataModel.put("showRememberMe", false);
        dataModel.put("rememberMeText", "Remember Me");
        dataModel.put("rememberMe", false);
        
        dataModel.put("showForgotPassword", false);
        dataModel.put("forgotPasswordText", "Forgot Password?");
        
        dataModel.put("showRegistration", false);
        dataModel.put("noAccountText", "Don't have an account?");
        dataModel.put("registerText", "Sign up");
        
        // Error testing - uncomment to test error display
        // dataModel.put("errorMessage", "Invalid username or password.");
        // dataModel.put("usernameError", "Please enter a valid username or email.");
        // dataModel.put("passwordError", "Password is required.");
        
        return dataModel;
    }

    private Map<String, Object> createErrorDataModel() {
        Map<String, Object> dataModel = new HashMap<>();
        
        // Basic template variables
        dataModel.put("title", "Login to Launchpad");
        dataModel.put("usernameLabel", "Username or Email");
        dataModel.put("passwordLabel", "Password");
        dataModel.put("loginButtonText", "Log In");
        dataModel.put("username", "testuser@example.com");
        
        // Optional features - all disabled
        dataModel.put("showRememberMe", false);
        dataModel.put("rememberMeText", "Remember Me");
        dataModel.put("rememberMe", false);
        
        dataModel.put("showForgotPassword", false);
        dataModel.put("forgotPasswordText", "Forgot Password?");
        
        dataModel.put("showRegistration", false);
        dataModel.put("noAccountText", "Don't have an account?");
        dataModel.put("registerText", "Sign up");
        
        // Error simulation for testing
        dataModel.put("errorMessage", "Invalid username or password. Please try again.");
        dataModel.put("usernameError", "Please enter a valid username or email address.");
        dataModel.put("passwordError", "Password cannot be empty.");
        
        return dataModel;
    }

    public static void main(String[] args) {
        try {
            KeycloakTemplateServer server = new KeycloakTemplateServer();
            server.start();
            
            // Keep the server running
            System.out.println("Press Ctrl+C to stop the server");
            Thread.currentThread().join();
            
        } catch (IOException e) {
            logger.severe("Failed to start server: " + e.getMessage());
            e.printStackTrace();
        } catch (InterruptedException e) {
            logger.info("Server interrupted");
            Thread.currentThread().interrupt();
        }
    }
}
