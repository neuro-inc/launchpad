#!/bin/bash

echo "Starting Keycloak Template Test Server..."
echo "This will compile and run the FreeMarker template server."
echo ""

# Check if Maven is installed
if ! command -v mvn &> /dev/null; then
    echo "Error: Maven is not installed or not in PATH"
    echo "Please install Maven to run this application"
    exit 1
fi

# Check if Java is installed
if ! command -v java &> /dev/null; then
    echo "Error: Java is not installed or not in PATH"
    echo "Please install Java 11 or higher to run this application"
    exit 1
fi

# Navigate to the script directory
cd "$(dirname "$0")"

echo "Compiling the application..."
mvn clean compile

if [ $? -eq 0 ]; then
    echo ""
    echo "Starting the server..."
    echo "The login page will be available at: http://localhost:8080/login"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    mvn exec:java
else
    echo "Compilation failed. Please check the error messages above."
    exit 1
fi
