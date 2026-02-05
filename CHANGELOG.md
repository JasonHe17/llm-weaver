# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Team/organization features
- Advanced monitoring and alerting
- More provider support (Mistral, Cohere, Wenxin, Qwen)
- Security audit features

## [1.1.0] - 2024-02-05

### Added
- **Smart Routing Engine** (`LoadBalancerService`)
  - 4 load balancing strategies: random, weighted, lowest_cost, performance
  - Health checks and automatic failover
  - Cache-aware routing for optimization
  - Performance metrics analysis (P50/P95/P99 latency)
- **Advanced Usage Statistics**
  - Token usage tracking (input/output)
  - Real-time cost calculation
  - Model-based and daily statistics
  - Usage dashboard with ECharts visualization
- **Enhanced Channel Management**
  - Health check APIs
  - Performance metrics APIs
  - Load balancer configuration APIs
- **Request Logging**
  - Detailed request/response logging
  - Error tracking
  - Filter by model and status
  - Pagination support

### Changed
- Improved API documentation with detailed examples
- Enhanced error handling with custom exception hierarchy
- Optimized database queries with proper indexing

### Fixed
- Token counting accuracy for various providers
- Budget limit enforcement timing

## [1.0.0] - 2024-01-15

### Added
- **User Authentication**
  - JWT-based authentication
  - User registration and login
  - Token refresh and logout
  - Password change functionality
- **API Key Management**
  - Create, read, update, delete API Keys
  - Regenerate and revoke functionality
  - Budget limits per API Key
  - Rate limiting support
  - IP whitelist configuration
  - Model access control
- **Channel Management**
  - Multi-provider channel configuration
  - Model mapping support
  - Channel testing functionality
  - Weight and priority configuration
- **OpenAI Compatible API**
  - `/v1/models` endpoint
  - `/v1/chat/completions` endpoint
  - Streaming and non-streaming responses
  - Multi-provider support (OpenAI, Anthropic, Azure, Gemini)
- **Usage Tracking**
  - Request logging
  - Token usage calculation
  - Cost tracking and calculation
  - Usage summary APIs
- **Management Dashboard**
  - Vue3 + TypeScript + Element Plus
  - Login page
  - Dashboard with charts
  - API Key management
  - Channel management
  - Usage statistics
  - Request logs viewer
  - Model management
  - Settings page
- **Deployment**
  - Docker and Docker Compose support
  - Nginx configuration
  - Prometheus and Grafana monitoring setup
- **Documentation**
  - Architecture documentation
  - API specification
  - Database design
  - Deployment guide
  - Development guide

### Technical Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 15+, Redis 7+
- **Frontend**: Vue 3, TypeScript, Element Plus, Pinia, Vue Router, ECharts
- **Infrastructure**: Docker, Nginx, Prometheus, Grafana

[Unreleased]: https://github.com/yourusername/llm-weaver/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/yourusername/llm-weaver/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yourusername/llm-weaver/releases/tag/v1.0.0
