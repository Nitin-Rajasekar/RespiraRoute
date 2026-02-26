import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, CircleMarker, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons (Leaflet + webpack issue)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const startIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const endIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Auto-fit bounds when data changes
function FitBounds({ bounds, boundsKey }) {
  const map = useMap();
  const fittedKeyRef = useRef(null);
  useEffect(() => {
    // Only fit bounds when the route changes (boundsKey), not on every data poll
    if (bounds && bounds.length > 0 && boundsKey !== fittedKeyRef.current) {
      map.fitBounds(bounds, { padding: [40, 40] });
      fittedKeyRef.current = boundsKey;
    }
  }, [map, bounds, boundsKey]);
  return null;
}

function RouteMap({ routeData, selectedRoute }) {
  if (!routeData || !routeData.routes || routeData.routes.length === 0) return null;

  const recommended = routeData.recommended;
  const hasGeometry = routeData.routes[0]?.geometry?.coordinates?.length > 0;

  // Build route lines — either from GeoJSON (custom routes) or zone coords (preset routes)
  const routeLines = routeData.routes.map((route) => {
    let positions;
    if (hasGeometry) {
      // Custom routes with OSRM GeoJSON
      const coords = route.geometry?.coordinates || [];
      positions = coords.map(([lng, lat]) => [lat, lng]);
    } else {
      // Preset routes — connect zone coordinates as waypoints
      positions = (route.zone_details || [])
        .filter(z => z.lat != null && z.lng != null)
        .map(z => [z.lat, z.lng]);
    }

    return {
      name: route.route_name,
      positions,
      isRecommended: route.route_name === recommended,
      isSelected: route.route_name === selectedRoute,
      exposure: route.total_exposure,
      zoneDetails: route.zone_details || [],
      startCoords: route.start_coords,
      endCoords: route.end_coords,
      start: route.start,
      end: route.end,
    };
  });

  // Determine which route to highlight
  const activeRoute = selectedRoute || recommended;

  // Sort: active route draws last (on top)
  const sorted = [...routeLines].sort((a, b) => {
    if (a.name === activeRoute) return 1;
    if (b.name === activeRoute) return -1;
    return 0;
  });

  // Collect all points for bounds
  const allPoints = [];
  const topLevelStart = routeData.start_coords;
  const topLevelEnd = routeData.end_coords;
  if (topLevelStart) allPoints.push(topLevelStart);
  if (topLevelEnd) allPoints.push(topLevelEnd);
  routeLines.forEach((r) => {
    r.positions.forEach((p) => allPoints.push(p));
    if (r.startCoords) allPoints.push(r.startCoords);
    if (r.endCoords) allPoints.push(r.endCoords);
  });

  if (allPoints.length === 0) return null;

  const center = topLevelStart || allPoints[0] || [28.6139, 77.209];

  const getColor = (route) => {
    if (route.name === activeRoute) return '#22c55e'; // green for active
    return '#64748b'; // slate for inactive
  };

  const getAqiColor = (aqi) => {
    if (aqi <= 50) return '#22c55e';   // green - good
    if (aqi <= 100) return '#84cc16';  // lime - moderate
    if (aqi <= 150) return '#eab308';  // yellow - unhealthy sensitive
    if (aqi <= 200) return '#f97316';  // orange - unhealthy
    if (aqi <= 300) return '#ef4444';  // red - very unhealthy
    return '#7c3aed';                   // purple - hazardous
  };

  // Split active route geometry into AQI-colored segments
  const buildColoredSegments = (route) => {
    if (!route.positions.length || !route.zoneDetails.length) return [];
    const totalPoints = route.positions.length;
    const numZones = route.zoneDetails.length;
    const segments = [];
    for (let i = 0; i < numZones; i++) {
      const startIdx = Math.round((i / numZones) * totalPoints);
      const endIdx = Math.round(((i + 1) / numZones) * totalPoints);
      // Include overlap point so segments connect seamlessly
      const segPositions = route.positions.slice(startIdx, Math.min(endIdx + 1, totalPoints));
      if (segPositions.length >= 2) {
        segments.push({
          positions: segPositions,
          aqi: route.zoneDetails[i].aqi,
          zone: route.zoneDetails[i].zone,
          color: getAqiColor(route.zoneDetails[i].aqi),
        });
      }
    }
    return segments;
  };

  // For preset routes, find the active route's start/end for markers
  const activeRouteData = routeLines.find(r => r.name === activeRoute) || routeLines[0];
  const showStart = topLevelStart || activeRouteData?.startCoords;
  const showEnd = topLevelEnd || activeRouteData?.endCoords;
  const startLabel = routeData.start || activeRouteData?.start;
  const endLabel = routeData.end || activeRouteData?.end;

  return (
    <div className="glass-card rounded-2xl overflow-hidden" style={{ height: '400px' }}>
      <MapContainer
        center={center}
        zoom={13}
        style={{ height: '100%', width: '100%', borderRadius: '1rem' }}
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds bounds={allPoints} boundsKey={routeData.routes.map(r => r.route_name).join('|') + '|' + (selectedRoute || '')} />

        {/* Draw routes */}
        {sorted.map((route) => {
          const isActive = route.name === activeRoute;

          if (isActive && hasGeometry && route.zoneDetails.length > 0) {
            // Active route: draw AQI-colored segments (like Google Maps traffic)
            const segments = buildColoredSegments(route);
            return (
              <React.Fragment key={route.name}>
                {segments.map((seg, i) => (
                  <Polyline
                    key={`${route.name}-seg-${i}`}
                    positions={seg.positions}
                    pathOptions={{
                      color: seg.color,
                      weight: 6,
                      opacity: 0.85,
                      lineCap: 'round',
                      lineJoin: 'round',
                    }}
                  >
                    <Popup>
                      <div style={{ color: '#1e293b', fontSize: '12px' }}>
                        <strong>{seg.zone}</strong>
                        <br />AQI: {seg.aqi}
                        <br />{route.isRecommended && <span style={{ color: '#16a34a' }}>Healthiest Route</span>}
                      </div>
                    </Popup>
                  </Polyline>
                ))}
              </React.Fragment>
            );
          }

          // Inactive routes: single solid line
          return (
            <React.Fragment key={route.name}>
              <Polyline
                positions={route.positions}
                pathOptions={{
                  color: getColor(route),
                  weight: isActive ? 5 : 3,
                  opacity: isActive ? 0.9 : 0.3,
                  dashArray: isActive ? null : '8 6',
                }}
              >
                <Popup>
                  <div style={{ color: '#1e293b', fontSize: '12px' }}>
                    <strong>{route.name}</strong>
                    <br />
                    Exposure: {route.exposure.toLocaleString()}
                  </div>
                </Popup>
              </Polyline>
            </React.Fragment>
          );
        })}

        {/* Start marker */}
        {showStart && (
          <Marker position={showStart} icon={startIcon}>
            <Popup>
              <span style={{ color: '#1e293b', fontSize: '12px' }}>
                <strong>Start:</strong> {startLabel}
              </span>
            </Popup>
          </Marker>
        )}

        {/* End marker */}
        {showEnd && (
          <Marker position={showEnd} icon={endIcon}>
            <Popup>
              <span style={{ color: '#1e293b', fontSize: '12px' }}>
                <strong>Destination:</strong> {endLabel}
              </span>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}

export default RouteMap;
