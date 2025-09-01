# Keycloak Template Test Server

This is a simple Java application that serves a FreeMarker template similar to the Keycloak login.ftl template for testing purposes.

## Prerequisites

- Java 11 or higher
- Maven 3.6 or higher

## Project Structure

```
keycloak-test/
├── pom.xml
├── src/
│   └── main/
│       ├── java/
│       │   └── com/
│       │       └── launchpad/
│       │           └── KeycloakTemplateServer.java
│       └── resources/
│           └── templates/
│               └── login.ftl
└── README.md
```

## How to Run

1. **Navigate to the project directory:**

   ```bash
   cd keycloak-test
   ```

2. **Install dependencies and compile:**

   ```bash
   mvn clean compile
   ```

3. **Run the application:**

   ```bash
   mvn exec:java
   ```

   Or alternatively:

   ```bash
   mvn clean compile exec:java -Dexec.mainClass="com.launchpad.KeycloakTemplateServer"
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:8080/login
   ```

## What This Does

- Starts a simple HTTP server on port 8080
- Serves the FreeMarker template with mock data
- Displays a login form styled similar to the Keycloak theme
- Shows how the custom CSS styling looks in a browser

## Template Features

The template includes:

- Clean, modern design with a white card on gray background
- Logo placeholder (using SVG)
- Form fields with labels positioned outside/above inputs
- Purple "Log In" button
- "Remember Me" checkbox
- "Forgot Password?" link
- "Sign up" registration link
- Responsive design

## Customization

You can modify the template data by editing the `createDataModel()` method in `KeycloakTemplateServer.java`.

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running to stop it.

## Notes

- This is a simplified version for testing purposes only
- The actual Keycloak theme files are in the `keycloak-theme/apolo/login/` directory
- This test server helps visualize how the styling will look without setting up a full Keycloak instance
