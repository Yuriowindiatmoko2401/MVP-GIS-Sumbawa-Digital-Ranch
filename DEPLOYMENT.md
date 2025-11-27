# Deployment Guide

This guide covers different deployment scenarios for the Sumbawa Digital Ranch MVP.

## 🐳 Docker Deployment (Recommended)

### Prerequisites
- Docker Engine 20.0+
- Docker Compose v2.0+
- At least 4GB RAM
- 10GB available disk space

### Production Deployment

1. **Clone the repository:**
```bash
git clone <repository-url>
cd MVP-GIS-Sumbawa-Digital-Ranch
```

2. **Create production environment files:**
```bash
# Backend production environment
cp backend/.env backend/.env.production

# Frontend production environment
cp frontend/.env frontend/.env.production
```

3. **Configure production environment:**
```bash
# backend/.env.production
DATABASE_URL=postgresql://postgres:YOUR_SECURE_PASSWORD@postgres:5432/sumbawa_gis
ENVIRONMENT=production
CORS_ORIGINS=["https://yourdomain.com"]
SECRET_KEY=your-secret-key-here

# frontend/.env.production
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
```

4. **Deploy with production Docker Compose:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

5. **Setup reverse proxy (Nginx):**
```nginx
# /etc/nginx/sites-available/sumbawa-gis
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Environment Setup

#### Development Environment
```bash
docker-compose up --build
```

#### Production Environment
```bash
# Create production network
docker network create gis-network

# Start database
docker-compose up -d postgres

# Wait for database to be ready
docker-compose logs -f postgres

# Start backend
docker-compose up -d backend

# Start frontend
docker-compose up -d frontend
```

## 🚀 Manual Deployment

### Database Setup

1. **Install PostgreSQL with PostGIS:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib postgis

# Create database
sudo -u postgres createdb sumbawa_gis

# Enable PostGIS extension
sudo -u postgres psql -d sumbawa_gis -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

2. **Initialize database schema:**
```bash
psql -U postgres -d sumbawa_gis -f backend/app/database/init_db.sql
```

### Backend Deployment

1. **Python environment:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

2. **Configuration:**
```bash
# Create .env file
cp .env.example .env
# Edit with your configuration
```

3. **Run backend:**
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production with Gunicorn
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend Deployment

1. **Node.js environment:**
```bash
cd frontend
npm install
```

2. **Development:**
```bash
npm run dev
```

3. **Production build:**
```bash
npm run build
# Serve the dist/ folder with your web server
```

## 🔒 Security Configuration

### Database Security
```sql
-- Create dedicated user
CREATE USER gis_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sumbawa_gis TO gis_user;

-- Restrict permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gis_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO gis_user;
```

### Backend Security
```python
# Use environment variables for secrets
import os
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-change-this")

# Enable HTTPS in production
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="path/to/key.pem",
        ssl_certfile="path/to/cert.pem"
    )
```

### Frontend Security
```javascript
// Content Security Policy
app.use((req, res, next) => {
    res.setHeader(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    );
    next();
});
```

## 📊 Monitoring & Logging

### Application Monitoring
```bash
# Application logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Database logs
docker-compose logs -f postgres

# System resource monitoring
docker stats
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/api/health

# Database connectivity
docker exec -it postgres-container pg_isready -U postgres -d sumbawa_gis
```

### Log Configuration
```python
# backend/app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/app.log"),
        logging.StreamHandler()
    ]
)
```

## 🔧 Performance Optimization

### Database Optimization
```sql
-- Create indexes for performance
CREATE INDEX idx_cattle_location ON cattle USING GIST (location);
CREATE INDEX idx_cattle_history_timestamp ON cattle_history (timestamp);
CREATE INDEX idx_cattle_history_location ON cattle_history USING GIST (location);

-- Analyze tables for query planner
ANALYZE cattle;
ANALYZE cattle_history;
ANALYZE resources;
ANALYZE geofences;

-- Vacuum for maintenance
VACUUM ANALYZE;
```

### Backend Performance
```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

### Frontend Performance
```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'leaflet'],
          router: ['vue-router']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  server: {
    hmr: {
      overlay: false
    }
  }
}
```

## 🔄 Backup & Recovery

### Database Backup
```bash
# Full backup
docker exec postgres-container pg_dump -U postgres sumbawa_gis > backup.sql

# Compressed backup
docker exec postgres-container pg_dump -U postgres -C sumbawa_gis | gzip > backup.sql.gz

# Restore
docker exec -i postgres-container psql -U postgres sumbawa_gis < backup.sql
```

### Automated Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="sumbawa_gis_backup_$DATE.sql.gz"

docker exec postgres-container pg_dump -U postgres -C sumbawa_gis | gzip > "$BACKUP_FILE"

# Keep only last 7 days
find . -name "sumbawa_gis_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

### Cron Job
```bash
# Add to crontab: crontab -e
0 2 * * * /path/to/backup.sh
```

## 🌐 CDN & Static Assets

### Frontend CDN Configuration
```javascript
// vite.config.js
export default {
  base: process.env.NODE_ENV === 'production' ? 'https://cdn.yourdomain.com/' : '/',
  build: {
    assetsDir: 'static',
    rollupOptions: {
      output: {
        assetFileNames: 'static/[name].[hash].[ext]'
      }
    }
  }
}
```

### Nginx Static Asset Caching
```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Cache-Status "STATIC";
}
```

## 🧪 Testing & Validation

### Load Testing
```bash
# Install k6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz

# Run load test
./k6 run load-test.js
```

### Health Check Validation
```bash
#!/bin/bash
# health-check.sh

API_URL="http://localhost:8000/api/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✅ Health check passed"
    exit 0
else
    echo "❌ Health check failed with status $RESPONSE"
    exit 1
fi
```

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  backend:
    scale: 3  # Run 3 backend instances

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
```

### Load Balancer Configuration
```nginx
upstream backend {
    server backend_1:8000;
    server backend_2:8000;
    server backend_3:8000;
}

server {
    location /api/ {
        proxy_pass http://backend;
        # Load balancing configuration
    }
}
```

This deployment guide covers various scenarios and best practices for deploying the Sumbawa Digital Ranch MVP in production environments.