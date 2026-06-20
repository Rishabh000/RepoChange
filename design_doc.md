# System Design Document

This document describes the high-level architecture of the service.

## Components
- API Gateway: routes and rate-limits inbound requests.
- Auth Service: issues and validates tokens (see auth notes).
- Core Service: business logic and persistence.
- Worker Pool: asynchronous jobs and scheduled tasks.

## Data Flow
Clients call the gateway, which forwards authenticated requests to the core
service. Long-running work is pushed onto a queue consumed by the worker pool.
