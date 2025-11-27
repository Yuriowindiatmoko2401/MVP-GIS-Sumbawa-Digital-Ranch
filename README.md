# Sumbawa Digital Ranch - MVP GIS

Real-time GPS cattle tracking and management system for Sumbawa Digital Ranch MVP.

## 🌟 Features

### Core Features
- **Real-time Cattle Tracking**: Live GPS tracking with WebSocket updates
- **Geofencing**: Automated boundary violation detection and alerts
- **Resource Management**: Water troughs, feeding stations, and shelter mapping
- **Heatmap Visualization**: Cattle movement patterns and density analysis
- **Health Monitoring**: Track cattle health status and generate alerts
- **Interactive Map**: Leaflet-based mapping with multiple layers
- **Real-time Notifications**: WebSocket-driven alert system
- **Dashboard Analytics**: Live statistics and monitoring

### Technical Features
- **PostgreSQL + PostGIS**: Spatial database for GPS and polygon data
- **FastAPI**: High-performance Python backend with WebSocket support
- **Vue 3**: Modern reactive frontend with Composition API
- **Pinia**: State management for Vue 3
- **Leaflet.js**: Interactive mapping and spatial visualization
- **Docker**: Containerized deployment with Docker Compose
- **Real-time Simulation**: Background tasks for cattle movement simulation

## 🏗️ Architecture

```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│   Vue 3 UI     │ ◄──────────────► │   FastAPI       │
│  (Leaflet.js)   │                  │   Backend       │
└─────────────────┘                  │                 │
                                     │   PostgreSQL    │
                                     │   + PostGIS     │
                                     └─────────────────┘
```

### Tech Stack

**Frontend:**
- Vue 3 with Composition API
- Pinia for state management
- Leaflet.js for mapping
- Axios for HTTP requests
- Vite for build tooling

**Backend:**
- FastAPI with WebSocket support
- SQLAlchemy ORM with GeoAlchemy2
- PostgreSQL with PostGIS extension
- Background task management
- Pydantic for data validation

**Infrastructure:**
- Docker & Docker Compose
- PostgreSQL with PostGIS
- Nginx (production ready)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (Recommended)
- OR Node.js 18+ and Python 3.11+

### Option 1: Docker Compose (Recommended)

1. **Clone and setup:**
```bash
git clone <repository-url>
cd MVP-GIS-Sumbawa-Digital-Ranch
```

2. **Start all services:**
```bash
docker-compose up --build
```

3. **Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Database: localhost:5432

### Option 2: Manual Development Setup

1. **Setup Database:**
```bash
# Start PostgreSQL with PostGIS
docker run -d --name postgres-gis \
  -e POSTGRES_DB=sumbawa_gis \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgis/postgis:16-3.4

# Initialize database
psql -h localhost -U postgres -d sumbawa_gis -f backend/app/database/init_db.sql
```

2. **Start Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. **Start Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 📋 API Documentation

### Core Endpoints

#### Health Check
```
GET /api/health
```

#### Cattle Management
```
GET    /api/cattle              # Get all cattle
GET    /api/cattle/{id}         # Get specific cattle
POST   /api/cattle              # Create new cattle
PUT    /api/cattle/{id}         # Update cattle
DELETE /api/cattle/{id}         # Delete cattle
GET    /api/cattle/history/{id}  # Get cattle history
```

#### Resources
```
GET    /api/resources           # Get all resources
GET    /api/resources/{type}    # Filter by type
POST   /api/resources           # Create resource
PUT    /api/resources/{id}      # Update resource
DELETE /api/resources/{id}      # Delete resource
```

#### Geofences
```
GET    /api/geofences           # Get all geofences
GET    /api/geofences/{id}      # Get specific geofence
POST   /api/geofences           # Create geofence
PUT    /api/geofences/{id}      # Update geofence
DELETE /api/geofences/{id}      # Delete geofence
```

#### Heatmap & Analytics
```
GET    /api/heatmap?hours=24    # Get heatmap data
GET    /api/stats               # Get general statistics
GET    /api/stats/cattle        # Get cattle statistics
```

### WebSocket Events

#### Client → Server
```javascript
{
  "type": "heartbeat",
  "timestamp": 1234567890
}
```

#### Server → Client
```javascript
// Cattle position updates
{
  "type": "cattle_update",
  "data": {
    "cattle": [...],
    "timestamp": "2025-11-27T10:29:00Z"
  }
}

// Geofence violations
{
  "type": "violation_alert",
  "data": {
    "alert": {
      "cattle_id": "uuid",
      "cattle_identifier": "SAPI-001",
      "current_location": {"lat": -8.123, "lng": 117.456},
      "violation_type": "LEFT_GEOFENCE"
    },
    "timestamp": "2025-11-27T10:29:00Z"
  }
}

// Heatmap refresh
{
  "type": "heatmap_refresh",
  "data": {
    "heatmap": [...],
    "hours": 24
  }
}
```

## 🗄️ Database Schema

### Tables

#### cattle
- `id` (UUID, Primary Key)
- `identifier` (String, Unique)
- `age` (Integer)
- `health_status` (Enum: Sehat, Perlu Perhatian, Sakit)
- `location` (PostGIS Point)
- `last_update` (Timestamp)

#### cattle_history
- `id` (UUID, Primary Key)
- `cattle_id` (Foreign Key)
- `location` (PostGIS Point)
- `timestamp` (Timestamp)

#### resources
- `id` (UUID, Primary Key)
- `resource_type` (Enum: water_trough, feeding_station, shelter)
- `name` (String)
- `location` (PostGIS Point)
- `capacity` (Integer, Optional)
- `current_usage` (Integer)

#### geofences
- `id` (UUID, Primary Key)
- `name` (String)
- `boundary` (PostGIS Polygon)
- `created_at` (Timestamp)

### Spatial Indexes
All geometry columns have GiST indexes for optimal spatial query performance.

## 🎨 Frontend Components

### Core Components

- **App.vue**: Main application component with layout and state management
- **MapViewer.vue**: Leaflet-based interactive map component
- **LayerControl.vue**: Toggle map layers and resources
- **NotificationPanel.vue**: Real-time alerts and notifications
- **CattleDetailsModal.vue**: Cattle information modal

### Services

- **wsService.js**: WebSocket client for real-time updates
- **apiService.js**: HTTP client for API communication
- **mapService.js**: Leaflet map utilities and helpers

### State Management (Pinia)

- **cattle.js**: Cattle data and operations
- **resources.js**: Resource management
- **geofences.js**: Geofence boundaries and operations
- **notifications.js**: Alert and notification system

## 🔧 Configuration

### Backend Environment (.env)
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/sumbawa_gis
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### Frontend Environment (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## 🧪 Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend
cd backend && python -m pytest

# Frontend
cd frontend && npm run test
```

### Code Quality
```bash
# Backend linting
cd backend && flake8 app/

# Frontend linting
cd frontend && npm run lint

# Frontend formatting
cd frontend && npm run format
```

## 🚀 Deployment

### Production Docker Setup
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up --build -d
```

### Environment Variables for Production
- `DATABASE_URL`: Production PostgreSQL connection
- `ENVIRONMENT`: Set to `production`
- `CORS_ORIGINS`: Production frontend URLs
- `SECRET_KEY`: FastAPI secret key

### Monitoring
- Application logs: `docker-compose logs -f`
- Database monitoring: Connect to pgAdmin on port 5050
- Health checks: http://localhost:8000/api/health

## 📊 Usage Examples

### Adding New Cattle
```bash
curl -X POST "http://localhost:8000/api/cattle" \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "SAPI-015",
    "age": 4,
    "health_status": "Sehat",
    "latitude": -8.657382,
    "longitude": 117.515206
  }'
```

### Creating Geofence
```bash
curl -X POST "http://localhost:8000/api/geofences" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Pasture",
    "boundary": {
      "type": "Polygon",
      "coordinates": [[
        [117.515, -8.657],
        [117.516, -8.657],
        [117.516, -8.658],
        [117.515, -8.658],
        [117.515, -8.657]
      ]]
    }
  }'
```

## 🔍 Troubleshooting

### Common Issues

#### Frontend won't connect to backend
1. Check if backend is running: `curl http://localhost:8000/api/health`
2. Verify CORS configuration in backend .env
3. Check browser console for connection errors

#### Database connection issues
1. Verify PostgreSQL is running: `docker ps`
2. Check database logs: `docker-compose logs postgres`
3. Test connection: `psql -h localhost -U postgres -d sumbawa_gis`

#### WebSocket connection fails
1. Check WebSocket endpoint: `wscat -c ws://localhost:8000/ws`
2. Verify no firewall blocking WebSocket connections
3. Check backend logs for WebSocket errors

#### Map not rendering
1. Verify Leaflet CSS is loaded
2. Check map container has proper height
3. Ensure map div has correct ID

#### Cattle markers not updating
1. Verify WebSocket connection is active
2. Check background tasks are running
3. Review browser Network tab for WebSocket messages

### Performance Tips

#### Large datasets (>1000 cattle)
- Enable marker clustering: `npm install leaflet.markercluster`
- Batch WebSocket updates (every 5 seconds instead of real-time)
- Use PostGIS spatial indexing

#### Database optimization
- Regular VACUUM and ANALYZE operations
- Monitor query performance with EXPLAIN ANALYZE
- Consider partitioning large tables by date

## 📈 Future Enhancements

### Planned Features
- **User Authentication**: Role-based access control
- **Mobile App**: React Native application
- **Historical Analytics**: Advanced data analysis tools
- **IoT Integration**: Real sensor data integration
- **Predictive Analytics**: ML-based cattle behavior prediction
- **Marketplace Integration**: Connect with livestock marketplace
- **Weather Integration**: Weather-based alerts and recommendations

### Technical Improvements
- **GraphQL API**: More efficient data fetching
- **Redis Caching**: Improve performance
- **Message Queue**: Better background task management
- **Microservices**: Split into specialized services
- **CDN Integration**: Static asset delivery
- **Automated Testing**: Increase test coverage

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/Vue
- Write meaningful commit messages
- Add tests for new features
- Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:

- **Documentation**: Check this README and API docs
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

## 🏆 Acknowledgments

- **Leaflet.js**: Excellent mapping library
- **FastAPI**: Modern Python web framework
- **PostGIS**: Powerful spatial database extension
- **Vue.js**: Progressive JavaScript framework
- **Docker**: Container platform for developers

---

**Sumbawa Digital Ranch - Empowering livestock management with technology** 🐄🌏