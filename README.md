# 🎵 Sound Your Scene - chatbot that finds music by mood, not metadata

[Click here to try this app - for a limited time!](http://soundyourscene.hirenotes.com/).<br/>
[Feedback and ideas welcome here](https://forms.gle/vtFnqH4F8oLQVrxi7)

This chatbot uses audio analysis of songs so you can search them by vibe. You can use a mood ("sad"), a purpose ("dancing"), a genre ("hip hop"), an era ("80s"), and even specific ranges for BPM (e.g. 90-120) and duration (e.g. "2-4 minutes"). You can add an image to help the bot understand the scene even better. This should be useful for finding music choices for a movie, TV show, or video game soundtrack.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Google AI](https://img.shields.io/badge/Google%20AI-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)

## 🚀 Workflow

This demo relies on [an open source dataset of about 18,000 songs from Youtube that were matched to their Spotify track ID](https://www.kaggle.com/datasets/salvatorerastelli/spotify-and-youtube), created 2/7/2023. This is just around 0.02% of the Spotify catalog, but still represents a sufficient selection of popular tracks. This data set was enriched with more metadata from Spotify, including audio analysis features. An LLM agent built leveraging the [Gemini API](https://ai.google.dev/) ingests the user's query and converts it to a set of filters and weights that are applied to the dataset. The LLM queries the data iteratively to refine the results, both autonomously and with user input.

## 🔧 How this was built

I first built a [Python Notebook](/notebooks/music-exploration.ipynb) to demo the concept end to end. Then, with the help of AI tools (Claude Code and Cursor) I converted this demo to a full stack web app, with a Python FastAPI back end, React front end, Postgres for persistence, and Redis for caching.

## 🚀 Features

### Core Functionality
- **Natural Language Search**: Describe any mood or scene in plain English
- **Image Search**: You can upload an optional image to further convey the mood you're searching for. Great if you're looking for selections for a film, TV series, or video game
- **AI-Powered Matching**: Google Gemini converts your query to a set of filters and weights, and then iteratively refines its search model based on results sample
- **Rich Audio Analysis**: Leverages Spotify's comprehensive audio feature set
- **Multi-Platform Results**: Integrated Spotify and YouTube links for each track

### Production Features
- **Scalable Architecture**: PostgreSQL database with Redis caching
- **Rate Limiting**: Smart protection against API abuse
- **Real-time Processing**: Background job processing with WebSocket-like polling
- **User Analytics**: Comprehensive tracking for search behavior and engagement
- **Playlist Management**: Create and share custom playlists
- **Email Integration**: Share playlists via email with security measures
- **Image Context**: Upload images to provide visual context for music searches
- **Performance Monitoring**: Built-in system health and performance metrics

## 🎯 Use Cases

- **Film & TV**: Find the perfect soundtrack for specific scenes
- **Content Creation**: Discover music that matches your video's mood
- **Game Development**: Source atmospheric music for different game states
- **Personal Discovery**: Explore music based on feelings rather than genres
- **DJs**: You can already give the chatbot specific BPM ranges, scales and modes coming soon

## 🏗️ Architecture

### Backend (Python FastAPI)
- **RESTful API**: Clean, documented endpoints with automatic OpenAPI generation
- **Async Processing**: Background job processing for LLM interactions
- **Database Layer**: SQLAlchemy ORM with PostgreSQL for persistence
- **Caching Strategy**: Redis for job status, rate limiting, and performance optimization
- **Security**: IP-based rate limiting, input validation, and secure file uploads

### Frontend (React + Vite)
- **Modern React**: Latest React 19 with functional components and hooks
- **Responsive Design**: Tailwind CSS for mobile-first, professional UI
- **Real-time Updates**: Polling mechanism for job status updates
- **Interactive Results**: Embedded YouTube players, sorting, and filtering
- **Progressive Enhancement**: Works without JavaScript for basic functionality

### Data Processing
- **Smart Filtering**: Multi-pass LLM refinement to reach optimal result counts
- **Feature Mapping**: Sophisticated translation from natural language to audio features
- **Result Ranking**: Intelligent scoring based on relevance and user preferences

## 🛠️ Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL with SQLAlchemy ORM
- Redis for caching and rate limiting
- Google Gemini AI for language processing
- Alembic for database migrations
- Gunicorn for production deployment

**Frontend:**
- React 19 with Vite build system
- Tailwind CSS for styling
- React Router for navigation
- Heroicons for consistent iconography
- Plotly.js for data visualizations

**Infrastructure:**
- Docker-ready deployment
- Environment-based configuration
- Comprehensive logging and monitoring
- Scalable worker architecture

## 📋 Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- PostgreSQL 13+
- Redis 6+
- Google AI API key
- Spotify Developer credentials

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
git clone https://github.com/[username]/soundbymood.git
cd soundbymood

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` file in the root directory. Follow the provided `.env.example` file. Requires credentials for the database, Redis host, Google AI API, Spotify API, and email sending.

### 3. Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Optional: Load sample data
python scripts/load_sample_data.py
```

### 4. Start Backend Services

```bash
# Development server
uvicorn api.main:app --reload --port 8000

# Or production server
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 5. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:5173` to access the application.

## 🧪 Development Workflow

### Running Tests

```bash
# Backend tests (not yet built)
pytest api/tests/

# Frontend tests (not yet built)
cd frontend && npm test

# Integration tests
pytest tests/integration/
```


### Database Management

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 📊 API Documentation

Once running, visit:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **Health Check**: `http://localhost:8000/health`

### Key Endpoints

```
POST /search              # Create new search job
GET  /jobs/{job_id}       # Get search results
POST /playlists           # Create/update playlist
GET  /playlists/{id}      # Get playlist for sharing
POST /upload-image        # Upload contextual image
GET  /stats               # System metrics dashboard
```

## 🚀 Deployment

### Production Deployment

```bash
# Use this script to build a deployment bundle
./create_deployment_bundle.sh

# Then deploy to your hosting platform
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### Environment Configuration

- **Development**: Auto-reload, CORS enabled, detailed logging
- **Production**: Gunicorn workers, optimized caching, security headers

## 📈 Performance & Monitoring

- **Health Checks**: Comprehensive system health monitoring
- **Rate Limiting**: IP-based protection with Redis backend  
- **Caching Strategy**: Multi-layer caching for optimal performance
- **Analytics**: User behavior tracking and engagement metrics
- **Error Handling**: Graceful degradation and comprehensive logging

## 🤝 Contributing

This project demonstrates production-ready full-stack development practices:

- Clean architecture with separation of concerns
- Comprehensive error handling and logging
- Security-first approach with rate limiting and input validation
- Scalable design patterns for high-traffic applications
- Modern development workflows with automated testing
- Professional API design with OpenAPI documentation

## 📄 License

This project is for portfolio demonstration and educational purposes. Please respect the terms of service for all integrated APIs (Spotify, Google AI, YouTube). Do not copy or deploy this, all rights reserved, (c) 2025. For contributions, ideas, or suggestions please contact me through [the feedback form](https://forms.gle/vtFnqH4F8oLQVrxi7).

---

**Built with ❤️ to showcase modern full-stack development practices**

*Combining the power of AI, music data science, and user-centered design*