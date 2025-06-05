# Contributing to SynApps

Thank you for your interest in contributing to SynApps! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Pull Request Process](#pull-request-process)
- [Creating Applets](#creating-applets)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

Our project adheres to a Code of Conduct that establishes expected behavior in our community. Please read [the full text](CODE_OF_CONDUCT.md) to understand what actions will and will not be tolerated.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork to your local machine:
   ```
   git clone https://github.com/yourusername/synapps-mvp.git
   ```
3. Add the original repository as an upstream remote:
   ```
   git remote add upstream https://github.com/synapps/synapps-mvp.git
   ```
4. Create a new branch for your feature or bugfix:
   ```
   git checkout -b feature/your-feature-name
   ```

## Development Environment

### Prerequisites

- Docker and Docker Compose
- Node.js 16+
- Python 3.9+
- API keys for OpenAI and Stability AI (for testing)

### Local Setup

1. Create a `.env` file in the root directory with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   STABILITY_API_KEY=your_stability_api_key
   ```

2. Install backend dependencies:
   ```
   cd apps/orchestrator
   pip install -e .
   ```

3. Install frontend dependencies:
   ```
   cd apps/web-frontend
   npm install
   ```

### Running the Application

#### Using Docker

```
docker-compose -f infra/docker/docker-compose.yml up
```

#### Manual Development

In one terminal:
```
cd apps/orchestrator
uvicorn main:app --reload
```

In another terminal:
```
cd apps/web-frontend
npm start
```

## Coding Standards

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style
- Use type hints where possible
- Document functions and classes with docstrings
- Use async/await for I/O-bound operations

### TypeScript/React

- Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use functional components with hooks
- Use TypeScript interfaces for props and state
- Keep components focused on a single responsibility

## Pull Request Process

1. Ensure your code follows the coding standards
2. Update documentation if necessary
3. Add tests for new functionality
4. Make sure all tests pass
5. Submit a pull request to the `main` branch
6. Wait for a maintainer to review your PR
7. Address any feedback from reviewers
8. Once approved, a maintainer will merge your PR

## Creating Applets

SynApps is designed to be extensible through custom applets. To create a new applet:

1. Create a new directory in `apps/applets/` with your applet name
2. Implement a class that extends `BaseApplet` and implements the required methods
3. Add tests for your applet in the `tests` directory
4. Document your applet's capabilities and usage
5. Submit a pull request following the process above

Example applet structure:

```
apps/applets/my-applet/
├── applet.py      # Main applet implementation
├── setup.py       # Package setup file
└── tests/         # Tests for your applet
    └── test_applet.py
```

## Testing

### Backend Testing

We use pytest for backend testing:

```
cd apps/orchestrator
pytest
```

### Frontend Testing

We use Jest and React Testing Library for frontend testing:

```
cd apps/web-frontend
npm test
```

### End-to-End Testing

We use Cypress for end-to-end testing:

```
cd apps/web-frontend
npm run test:e2e
```

## Documentation

Good documentation is crucial for the project. Please update the following as needed:

- README.md for overview and quick start
- In-line code comments for complex logic
- API documentation using docstrings
- Update architecture.md for design changes
- Add usage examples for new features

## Community

Join our community to discuss development, get help, and share your work:

- [Discord Server](https://discord.gg/synapps)
- [GitHub Discussions](https://github.com/synapps/synapps-mvp/discussions)
- [Twitter](https://twitter.com/synappshq)

## License

By contributing to SynApps, you agree that your contributions will be licensed under the project's MIT License.
