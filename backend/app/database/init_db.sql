-- PostgreSQL + PostGIS initialization script for Sumbawa Digital Ranch MVP
-- Creates database schema, spatial indexes, and dummy data

-- Create database (run this manually before connecting)
-- CREATE DATABASE sumbawa_gis;
-- \c sumbawa_gis;

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create enum types
CREATE TYPE health_status_enum AS ENUM ('Sehat', 'Perlu Perhatian', 'Sakit');
CREATE TYPE resource_type_enum AS ENUM ('water_trough', 'feeding_station', 'shelter');

-- Cattle table - main livestock tracking data
CREATE TABLE cattle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(50) UNIQUE NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0 AND age < 30),
    health_status health_status_enum NOT NULL DEFAULT 'Sehat',
    location GEOMETRY(POINT, 4326) NOT NULL,  -- WGS84 coordinates
    last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_location CHECK (location IS NOT NULL AND ST_IsValid(location))
);

-- Cattle history table - GPS tracking history
CREATE TABLE cattle_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cattle_id UUID NOT NULL REFERENCES cattle(id) ON DELETE CASCADE,
    location GEOMETRY(POINT, 4326) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_history_location CHECK (location IS NOT NULL AND ST_IsValid(location))
);

-- Resources table - water, feed, shelter locations
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type resource_type_enum NOT NULL,
    name VARCHAR(200) NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    description TEXT,
    capacity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_resource_location CHECK (location IS NOT NULL AND ST_IsValid(location))
);

-- Geofences table - ranch boundaries and restricted areas
CREATE TABLE geofences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    boundary GEOMETRY(POLYGON, 4326) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_boundary CHECK (boundary IS NOT NULL AND ST_IsValid(boundary))
);

-- Create spatial indexes for performance
CREATE INDEX idx_cattle_location ON cattle USING GIST (location);
CREATE INDEX idx_cattle_history_location ON cattle_history USING GIST (location);
CREATE INDEX idx_cattle_history_timestamp ON cattle_history (timestamp);
CREATE INDEX idx_resources_location ON resources USING GIST (location);
CREATE INDEX idx_geofences_boundary ON geofences USING GIST (boundary);

-- Create composite indexes for common queries
CREATE INDEX idx_cattle_history_cattle_timestamp ON cattle_history (cattle_id, timestamp DESC);

-- Insert dummy data for MVP testing

-- Main ranch geofence (Sumbawa area - approximate coordinates around Sumbawa Besar)
INSERT INTO geofences (name, boundary, description) VALUES
(
    'Sumbawa Digital Ranch Main Area',
    ST_GeomFromText('POLYGON((117.35 -8.52, 117.35 -8.48, 117.42 -8.48, 117.42 -8.52, 117.35 -8.52))', 4326),
    'Main ranch boundary for cattle management area in Sumbawa Besar region'
);

-- Insert dummy cattle (10 cattle within the geofence)
INSERT INTO cattle (identifier, age, health_status, location) VALUES
('SAPI-001', 4, 'Sehat', ST_GeomFromText('POINT(117.37 -8.50)', 4326)),
('SAPI-002', 3, 'Sehat', ST_GeomFromText('POINT(117.38 -8.49)', 4326)),
('SAPI-003', 5, 'Perlu Perhatian', ST_GeomFromText('POINT(117.36 -8.51)', 4326)),
('SAPI-004', 2, 'Sehat', ST_GeomFromText('POINT(117.39 -8.50)', 4326)),
('SAPI-005', 6, 'Sehat', ST_GeomFromText('POINT(117.37 -8.49)', 4326)),
('SAPI-006', 3, 'Sehat', ST_GeomFromText('POINT(117.38 -8.51)', 4326)),
('SAPI-007', 4, 'Sakit', ST_GeomFromText('POINT(117.36 -8.50)', 4326)),
('SAPI-008', 1, 'Sehat', ST_GeomFromText('POINT(117.39 -8.49)', 4326)),
('SAPI-009', 5, 'Sehat', ST_GeomFromText('POINT(117.37 -8.51)', 4326)),
('SAPI-010', 3, 'Sehat', ST_GeomFromText('POINT(117.38 -8.50)', 4326));

-- Insert some history data for testing heatmap
INSERT INTO cattle_history (cattle_id, location, timestamp)
SELECT
    c.id,
    ST_Translate(
        c.location,
        (random() - 0.5) * 0.002,  -- Random movement within ~200m
        (random() - 0.5) * 0.002
    ),
    NOW() - (random() * INTERVAL '24 hours')
FROM cattle c
JOIN generate_series(1, 5) s ON true;  -- 5 history entries per cattle

-- Insert water resources
INSERT INTO resources (resource_type, name, location, description, capacity) VALUES
('water_trough', 'Water Point 1', ST_GeomFromText('POINT(117.37 -8.50)', 4326), 'Main water trough for northern area', 50),
('water_trough', 'Water Point 2', ST_GeomFromText('POINT(117.39 -8.49)', 4326), 'Water trough for southern area', 40),
('water_trough', 'Water Point 3', ST_GeomFromText('POINT(117.38 -8.51)', 4326), 'Central water supply', 60);

-- Insert feeding stations
INSERT INTO resources (resource_type, name, location, description, capacity) VALUES
('feeding_station', 'Feed Station A', ST_GeomFromText('POINT(117.36 -8.49)', 4326), 'Main feeding area for young cattle', 20),
('feeding_station', 'Feed Station B', ST_GeomFromText('POINT(117.38 -8.50)', 4326), 'Feeding area for adult cattle', 30);

-- Insert shelter areas
INSERT INTO resources (resource_type, name, location, description, capacity) VALUES
('shelter', 'Shelter 1', ST_GeomFromText('POINT(117.37 -8.51)', 4326), 'Covered shelter area', 25),
('shelter', 'Shelter 2', ST_GeomFromText('POINT(117.39 -8.50)', 4326), 'Open-sided shelter', 35);

-- Create view for current cattle positions with details
CREATE VIEW cattle_current AS
SELECT
    c.id,
    c.identifier,
    c.age,
    c.health_status,
    ST_X(c.location) as lng,
    ST_Y(c.location) as lat,
    c.last_update,
    c.created_at
FROM cattle c;

-- Create view for resources with coordinates
CREATE VIEW resources_geojson AS
SELECT
    r.id,
    r.resource_type,
    r.name,
    r.description,
    r.capacity,
    ST_X(r.location) as lng,
    ST_Y(r.location) as lat,
    ST_AsGeoJSON(r.location) as geojson,
    r.created_at
FROM resources r;

-- Create view for geofences with coordinates
CREATE VIEW geofences_geojson AS
SELECT
    g.id,
    g.name,
    g.description,
    g.is_active,
    ST_AsGeoJSON(g.boundary) as geojson,
    g.created_at
FROM geofences g
WHERE g.is_active = TRUE;

-- Useful spatial queries for reference:

-- Query to find cattle outside geofence:
-- SELECT c.identifier, c.location FROM cattle c, geofences g
-- WHERE NOT ST_Within(c.location, g.boundary) AND g.name = 'Sumbawa Digital Ranch Main Area';

-- Query to get cattle near resources (within 100 meters):
-- SELECT c.identifier, r.name, r.resource_type, ST_Distance(c.location, r.location) as distance_meters
-- FROM cattle c, resources r
-- WHERE ST_DWithin(c.location, r.location, 100/111000)  -- 100 meters in degrees
-- ORDER BY distance_meters;

-- Query for heatmap data aggregation (grid cells 100m x 100m):
-- SELECT
--     FLOOR(ST_X(location) * 10000) / 10000 as grid_lng,
--     FLOOR(ST_Y(location) * 10000) / 10000 as grid_lat,
--     COUNT(*) as intensity
-- FROM cattle_history
-- WHERE timestamp > NOW() - INTERVAL '24 hours'
-- GROUP BY grid_lng, grid_lat;

-- Grant permissions if needed (uncomment for production)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sumbawa_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sumbawa_user;

-- Summary of data created
SELECT 'Database initialization completed!' as status;
SELECT COUNT(*) as cattle_count FROM cattle;
SELECT COUNT(*) as history_records FROM cattle_history;
SELECT COUNT(*) as resources FROM resources;
SELECT COUNT(*) as geofences FROM geofences;