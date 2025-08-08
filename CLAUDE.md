# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sound your scene is a demo AI-powered music discovery platform that enables users to find music through natural language descriptions rather than traditional metadata searches. The system combines Spotify's comprehensive audio analysis features with Google's Gemini AI to provide intelligent, contextually-aware music recommendations.

**Live Demo**: [soundyourscene.hirenotes.com](http://soundyourscene.hirenotes.com/)

**Original Python Notebook**: [music-exploration.ipynb](/notebooks/music-exploration.ipynb). Your job is to convert this demo of how the search function works to a full stack, production grade, web application.

## Core Concept

Instead of searching by song titles, artists, or genres, users can describe scenarios like:
- "Music for a tense confrontation scene in a period drama"
- "Upbeat electronic music for a millennium dance party"
- "Brooding ambient tracks for a cyberpunk game"
- "Nostalgic 1970s vibes for a coming-of-age film"

The system uses LLM agents to convert these descriptions into precise audio feature filters, then applies iterative refinement to optimize result quality.

## Architecture Overview

### Production Stack
- **Backend**: FastAPI (Python 3.11+) with async processing
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for performance optimization and rate limiting
- **Frontend**: React 19 with Vite build system and Tailwind CSS
- **AI Processing**: Google Gemini API for natural language understanding
- **Data Sources**: Spotify API + YouTube integration with 18K+ track dataset

### Key Production Features
- **Scalable Job Processing**: Async background tasks with status tracking
- **Rate Limiting & Security**: IP-based protection with Redis backend
- **Real-time Analytics**: User behavior tracking and engagement metrics
- **Email Service**: Secure playlist sharing with abuse prevention
- **Image Processing**: Visual context for mood-based searches
- **Health Monitoring**: Comprehensive system metrics and alerting
- **Multi-environment**: Development and production configurations

## User Experience Flow

### 1. Initial Search Interface
- **Example Categories**: 5 predefined mood categories with icons:
  - Period drama (classical/orchestral vibes)
  - Millennial dance party (2000s pop/electronic)
  - Brooding electro (dark electronic/ambient)
  - OG rap (classic hip-hop)
  - 1970s nostalgia (vintage rock/soul)
- **Custom Input**: Free-form text input for unique descriptions
- **Image Context**: Optional image upload for visual mood reference

### 2. AI Processing Pipeline
- **Query Analysis**: LLM converts natural language to audio feature filters
- **Iterative Refinement**: Up to 3 passes to optimize result count (target: 20-50 tracks)
- **Feature Mapping**: Translation to Spotify audio analysis parameters:
  - Valence (emotional positivity)
  - Energy and danceability
  - Acousticness and instrumentalness
  - Tempo and key signature
  - Loudness and speechiness

### 3. Results Experience
- **Rich Metadata Display**: Title, artist, release date, genres, explicit content flags
- **Multi-platform Access**: Direct Spotify and YouTube links
- **Interactive Features**: Embedded YouTube players, audio feature visualizations
- **Sorting Options**: Relevance, recency, popularity, duration
- **Conversation Flow**: Chat-based refinement with AI agent

### 4. Playlist & Sharing
- **Playlist Creation**: Save and organize selected tracks
- **Email Sharing**: Secure playlist distribution with rate limiting
- **Export Options**: Multiple format support for external use

## Database Schema

### Core Tables
- **user_sessions**: Track user interactions and IP addresses
- **search_sessions**: Store search queries and AI conversation history
- **search_results**: Individual track results with relevance scoring
- **playlists**: User-created track collections linked to search sessions
- **track_events**: Analytics for user engagement (clicks, plays, bookmarks)
- **email_sends**: Audit trail for playlist sharing with security controls

### Key Relationships
- User sessions → Multiple search sessions
- Search sessions → Multiple results + optional playlist
- Results → Track events for analytics
- Playlists → Email sends for sharing

## API Architecture

### Core Endpoints
```
POST /search              # Create async search job, return job_id
GET  /jobs/{job_id}       # Poll job status and retrieve results
POST /playlists           # Create/update playlist from search results
GET  /playlists/{id}      # Retrieve playlist for sharing (increments access_count)
POST /upload-image        # Upload contextual image for mood analysis
POST /track-events        # Analytics endpoint for user interactions
POST /playlists/{id}/email # Secure email sharing with rate limits
GET  /stats               # System metrics and dashboard data
GET  /health              # Load balancer health check
```

### Production Considerations
- **Async Processing**: Long-running AI tasks handled in background
- **Job Status Tracking**: Real-time progress updates via polling
- **Rate Limiting**: Multi-tier limits (per minute/hour/day) with Redis
- **Security**: Input validation, file upload restrictions, XSS protection
- **Monitoring**: Performance metrics, error tracking, system health

## Frontend Architecture

### Component Hierarchy
```
App
├── SearchForm
│   ├── ExampleTabs (5 preset moods + custom)
│   ├── ImageUpload (optional visual context)
│   └── SearchInput (natural language text)
├── SearchResults
│   ├── LoadingMessage (job status polling)
│   ├── ChainOfThought (AI reasoning display)
│   ├── ResultsList
│   │   └── TrackView (YouTube embed + metadata + actions)
│   └── VolumeMetrics (feature visualizations)
├── ChatHistory (conversation with AI)
├── PlaylistView (saved tracks management)
└── Dashboard (analytics - admin only)
```

### State Management
- **useSearch Hook**: Centralized search state and job polling
- **Local Storage**: User session persistence and playlist caching
- **Context Providers**: User session and analytics tracking
- **Service Layer**: API calls abstracted through dedicated services

## Development Workflow

### Environment Setup
```bash
# Backend setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database initialization
alembic upgrade head

# Frontend setup
cd frontend && npm install

# Development servers
uvicorn api.main:app --reload --port 8000  # Backend
npm run dev                                  # Frontend (port 5173)
```

### Key Development Commands
```bash
# Database operations
alembic revision --autogenerate -m "Description"  # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                              # Rollback migration

# Frontend operations
npm run build                    # Production build
npm run lint                     # ESLint checking
npm run preview                  # Preview production build

# Testing (planned)
pytest api/tests/               # Backend tests
npm test                        # Frontend tests
```

### Deployment Process
```bash
# Build production bundle
cd frontend && npm run build
cp -r dist/* ../api/static/

# Create deployment package
./create_deployment_bundle.sh

# Production deployment (example)
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## AI Integration Strategy

### LLM Processing Pipeline
1. **Query Understanding**: Parse user intent and extract mood descriptors
2. **Feature Translation**: Map natural language to Spotify audio features
3. **Initial Filtering**: Apply broad filters to dataset
4. **Iterative Refinement**: Narrow results through multiple passes
5. **Result Optimization**: Target 20-50 high-quality matches
6. **Explanation Generation**: Provide reasoning for track selections

### Prompt Engineering
- **System Prompts**: Structured templates for consistent AI behavior
- **Context Management**: Conversation history for iterative refinement
- **Feature Constraints**: Bounded ranges for audio analysis parameters
- **Quality Assurance**: Validation of AI-generated filter sets

## Performance & Scaling

### Caching Strategy
- **Redis Implementation**: Job status, rate limits, frequently accessed data
- **Database Optimization**: Indexed queries, connection pooling
- **Static Assets**: CDN-ready frontend build with asset optimization

### Monitoring & Analytics
- **System Health**: Memory usage, CPU load, Redis connectivity
- **User Analytics**: Search patterns, engagement metrics, conversion rates
- **Performance Tracking**: Response times, error rates, throughput metrics
- **Business Intelligence**: Popular queries, successful matches, user retention

## Security Implementation

### Protection Measures
- **Rate Limiting**: Multi-tier IP-based restrictions with Redis backend
- **Input Validation**: Pydantic models for request validation
- **File Upload Security**: Type validation, size limits, malware scanning
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Content sanitization and CSP headers

### Privacy Considerations
- **Data Minimization**: Limited personal data collection
- **Session Management**: Temporary user sessions without persistent auth
- **Email Security**: Rate limiting and abuse prevention for sharing features

## Testing Strategy (Planned)

### Backend Testing
- **Unit Tests**: Individual service and utility function testing
- **Integration Tests**: Database operations and API endpoint validation
- **Performance Tests**: Load testing for concurrent user scenarios

### Frontend Testing
- **Component Tests**: React component behavior and rendering
- **Integration Tests**: User flow and API interaction testing
- **E2E Tests**: Complete user journey validation

## Technical Debt & Future Enhancements

### Current Limitations
- Test suite implementation (unit, integration, e2e)
- Container orchestration (Docker Compose setup)
- CI/CD pipeline configuration
- Advanced analytics dashboard
- Mobile app considerations

### Planned Improvements
- **Advanced AI Features**: Multi-modal input processing, mood evolution tracking
- **Enhanced Dataset**: Expanded music catalog, additional audio features
- **Social Features**: User accounts, playlist sharing, collaborative filtering
- **Performance Optimization**: Advanced caching, database sharding, CDN integration

## Data Sources & Attribution

### Primary Dataset
- **Source**: [Spotify-YouTube Dataset](https://www.kaggle.com/datasets/salvatorerastelli/spotify-and-youtube) (18K+ tracks)
- **Enhancement**: Enriched with additional Spotify metadata and audio analysis
- **Coverage**: Represents ~0.02% of Spotify catalog but covers popular tracks across genres
- **Last Updated**: February 2023

### API Integrations
- **Spotify Web API**: Track metadata, audio features, artist information
- **YouTube Data API**: Video information, embedding capabilities
- **Google Gemini API**: Natural language processing and reasoning

This architecture demonstrates production-ready full-stack development with emphasis on scalability, security, and user experience. The codebase showcases modern development practices including async processing, comprehensive monitoring, and AI integration patterns suitable for enterprise applications.