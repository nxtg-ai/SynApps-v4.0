# SynApps v4.0

A web-based visual platform for modular AI agents with database persistence and improved workflow execution.

## Introduction

SynApps is a **web-based visual platform for modular AI agents**. Its mission is to let indie creators build autonomous AI applets like LEGO blocks – each applet is a small agent with a specialized skill (e.g. *Writer*, *Memory*, *Artist*). 

A lightweight **SynApps Orchestrator** routes messages between these applets, sequencing their interactions to solve tasks collaboratively. In other words, SynApps connects AI "synapses" (agents) in real time, forming an intelligent network that can tackle complex workflows.

## Features

- **One-Click Creation & Extreme Simplicity:** Create an AI workflow with minimal steps (one or two clicks).
- **Autonomous & Collaborative Agents:** Each applet (agent) runs autonomously but can pass data to others via the orchestrator.
- **Real-Time Visual Feedback:** See the AI agents at work with an animated graph of nodes (agents) and connections (data flow).
- **Background Execution & Notifications:** Agents run in the background once triggered, with a notification system to alert users of important status changes.
- **Openness and Extensibility:** Support for user-editable applets via code for those who want to customize logic.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- Optionally: Node.js 16+ and Python 3.9+ for local development

### Running with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/nxtg-ai/SynApps-v4.0.git
   cd SynApps-v4.0
   ```

2. Create a `.env` file in the root of the project with your API keys and database URL:
   ```
   OPENAI_API_KEY=your_openai_api_key
   STABILITY_API_KEY=your_stability_api_key
   DATABASE_URL=sqlite+aiosqlite:///synapps.db
   ```

3. Build and run the containers:
   ```bash
   docker-compose -f infra/docker/docker-compose.yml up
   ```

4. Open your browser and navigate to [http://localhost:3000](http://localhost:3000)

### Local Development

#### Backend (Orchestrator)

1. Navigate to the orchestrator directory:
   ```bash
   cd apps/orchestrator
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   alembic upgrade head
   ```

4. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd apps/web-frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm start
   ```

## Architecture

SynApps follows a microkernel architecture:

- **Orchestrator:** A lightweight message routing core that passes data between applets and manages workflow execution.
- **Applets:** Self-contained AI micro-agents implementing a standard interface to perform specialized tasks.
- **Frontend:** React app with a visual workflow editor, built on React Flow and anime.js for animations.
- **Database:** SQLite with async SQLAlchemy ORM for persistent storage of workflows and execution state.

## Applets

The MVP includes three core applets:

- **WriterApplet:** Generates text given a topic or prompt using gpt-4.1.
- **MemoryApplet:** Stores or retrieves information to maintain context between steps using a vector store.
- **ArtistApplet:** Creates an image from a text description using Stable Diffusion.

## Deployment

The application is configured for deployment to:

- **Frontend:** Vercel
- **Backend:** Fly.io

CI/CD pipelines are set up using GitHub Actions.

## Database

SynApps v4.0 uses SQLAlchemy with async support for database operations:

- **ORM Models:** SQLAlchemy models for flows, nodes, edges, and workflow runs
- **Migrations:** Alembic for database schema migrations
- **Repository Pattern:** Clean separation of database access logic
- **Async Support:** Full async/await pattern for database operations

## Development Workflow

1. Create a feature branch from `main`
2. Make your changes
3. Write tests for your changes
4. Submit a pull request to `main`
5. After review and approval, the changes will be merged and deployed automatically

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [React Flow](https://reactflow.dev/) for the workflow visualization
- [anime.js](https://animejs.com/) for animations
- [FastAPI](https://fastapi.tiangolo.com/) for the backend
- [Monaco Editor](https://microsoft.github.io/monaco-editor/) for the code editor
