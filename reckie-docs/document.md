# Vision Document

## Introduction
This document outlines the vision for a new application designed to serve as an OpenID Connect (OIDC) identity and authentication token provider, reverse proxy, and API gateway.

## Purpose
The purpose of this application is to facilitate secure and efficient authentication and authorization for various applications by providing a centralized OIDC token service. Additionally, it will serve as a reverse proxy and gateway to manage API requests to multiple backend services.

## Business Goals
- Provide a reliable OIDC and authentication token service for client applications.
- Simplify backend service management through a unified API gateway.
- Enhance security by injecting authentication bearer tokens for service requests.
- Improve maintainability and scalability of authentication services.

## Target Audience
- Software developers and architects who require secure authentication solutions.
- Businesses looking to implement centralized identity management and API gateway.
- IT administrators managing multiple backend services.

## Stakeholders
- Development teams integrating OIDC services in their applications.
- IT departments responsible for maintaining authentication systems.
- Product managers overseeing the deployment of secure applications.

## Scope and Limitations
### Scope
- The application will support generating OIDC and authentication tokens.
- It will act as a reverse proxy to inject bearer tokens into HTTP requests.
- Serve as an API gateway to multiple backend services.
- Provide endpoints compliant with standard OAuth flows.

### Limitations
- The application will be a console app written in Java.
- Authentication tokens will be stored in memory, which may limit scalability.

## Assumptions and Dependencies
- The application assumes a stable Java runtime environment.
- It relies on configuration files for identifying OIDC client IDs.
- Dependency on backend services being available and properly configured.

## Risks
- Security risks associated with handling authentication tokens.
- Potential performance bottlenecks due to in-memory token storage.
- Complexity in managing configuration files for multiple client IDs.

## High-Level Requirements
- Implement OIDC token generation and validation endpoints.
- Develop functionality for reverse proxy with token injection.
- Design API gateway to route requests to appropriate backend services.
- Ensure the application supports OAuth code flow.

## Success Criteria
- Successful generation and validation of OIDC and authentication tokens.
- Seamless integration with backend services via API gateway.
- Secure and reliable management of authentication processes.
- Positive feedback from developers and IT administrators.

## Conclusion
This vision document serves as a guide for the development of a comprehensive application supporting OIDC token services, reverse proxy functionalities, and API gateway capabilities. The successful implementation will enhance security and simplify the management of backend services for various applications.
