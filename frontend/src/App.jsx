import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import ZoneCards from './components/ZoneCards';
import RouteComparison from './components/RouteComparison';
import HealthGauge from './components/HealthGauge';
import AiPanel from './components/AiPanel';
import RouteSearch from './components/RouteSearch';
import RouteMap from './components/RouteMap';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [customRoutes, setCustomRoutes] = useState(null);
  const [enrichingNames, setEnrichingNames] = useState(false);
  const [selectedCity, setSelectedCity] = useState(null); // null = city overview
  const [selectedRoute, setSelectedRoute] = useState(null); // which route card is selected
  const [insights, setInsights] = useState([]); // Pathway LLM anomaly insights

  const fetchDashboard = useCallback(async () => {
    try {
      const url = selectedCity
        ? `${API_BASE}/api/dashboard?city=${encodeURIComponent(selectedCity)}`
        : `${API_BASE}/api/dashboard`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      setDashboard(data);
      setConnected(true);
      setLastUpdate(new Date());
      setError(null);
    } catch (err) {
      setError('Cannot connect to backend. Make sure the server is running on port 8000.');
      setConnected(false);
    }
  }, [selectedCity]);

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 2000);
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  // Fetch Pathway LLM anomaly insights when inside a city
  useEffect(() => {
    if (!selectedCity) { setInsights([]); return; }
    const fetchInsights = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/anomaly-insights?city=${encodeURIComponent(selectedCity)}`);
        if (res.ok) {
          const data = await res.json();
          setInsights(data.insights || []);
        }
      } catch { /* ignore */ }
    };
    fetchInsights();
    const interval = setInterval(fetchInsights, 5000);
    return () => clearInterval(interval);
  }, [selectedCity]);

  const zones = dashboard?.zones || {};
  const anomalies = dashboard?.anomalies || [];
  // Only show routes when user searches for them
  const activeRoutes = customRoutes;

  const handleEnrichNames = async () => {
    if (!customRoutes) return;
    setEnrichingNames(true);
    const allCoords = customRoutes.routes.flatMap(r =>
      r.zone_details.map(z => ({ lat: z.lat, lng: z.lng }))
    );
    try {
      const res = await fetch(`${API_BASE}/api/enrich-route-names`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coords: allCoords }),
      });
      const data = await res.json();
      let idx = 0;
      const enriched = {
        ...customRoutes,
        routes: customRoutes.routes.map(r => ({
          ...r,
          zone_details: r.zone_details.map(z => ({
            ...z,
            zone: data.names[idx++] || z.zone,
          })),
        })),
      };
      setCustomRoutes(enriched);
    } catch { /* ignore */ } finally {
      setEnrichingNames(false);
    }
  };

  const handleCityClick = (cityName) => {
    setSelectedCity(cityName);
    setCustomRoutes(null);
    setSelectedRoute(null);
  };

  const handleBackToCities = () => {
    setSelectedCity(null);
    setCustomRoutes(null);
    setSelectedRoute(null);
  };

  // Auto-select recommended route when search results arrive
  useEffect(() => {
    if (customRoutes?.recommended && !selectedRoute) {
      setSelectedRoute(customRoutes.recommended);
    }
  }, [customRoutes?.recommended, selectedRoute]);

  return (
    <div className="min-h-screen bg-slate-950">
      <Header connected={connected} lastUpdate={lastUpdate} />

      {error && (
        <div className="max-w-7xl mx-auto px-4 pt-4">
          <div className="glass-card rounded-xl p-4 border-l-4 border-red-500">
            <p className="text-red-400 text-sm font-medium">{error}</p>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Custom Route Search — only shown when inside a city */}
        {selectedCity && (
          <RouteSearch
            onResults={(data) => { setCustomRoutes(data); setSelectedRoute(null); }}
            onClear={() => { setCustomRoutes(null); setSelectedRoute(null); }}
          />
        )}

        {/* Health Gauge + Route Comparison + Map — shown in city drill-down */}
        {selectedCity && (
          <>
            {/* Route header — shows what routes are being displayed */}
            {activeRoutes?.routes?.length > 0 && (
              <div className="flex items-center justify-between glass-card rounded-xl px-5 py-3">
                <h2 className="text-sm font-semibold text-emerald-400 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                  {activeRoutes?.start && activeRoutes?.end
                    ? <>{activeRoutes.start} → {activeRoutes.end}</>
                    : <>Routes in {selectedCity}</>
                  }
                </h2>
              </div>
            )}

            {/* Route results — only shown after a search */}
            {activeRoutes && (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-1">
                    <HealthGauge
                      routes={activeRoutes}
                      selectedRoute={selectedRoute}
                    />
                  </div>
                  <div className="lg:col-span-2">
                    <RouteComparison
                      routes={activeRoutes}
                      selectedRoute={selectedRoute}
                      onSelectRoute={setSelectedRoute}
                      onEnrichNames={handleEnrichNames}
                      enrichingNames={enrichingNames}
                    />
                  </div>
                </div>
                <RouteMap routeData={activeRoutes} selectedRoute={selectedRoute} />
              </>
            )}
          </>
        )}

        {/* Zone Cards (cities or zones) */}
        <section>
          <h2 className="text-lg font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {selectedCity
              ? `${selectedCity} — Zone Monitoring`
              : 'Indian Cities — Live AQI'}
          </h2>
          <ZoneCards
            zones={zones}
            isCity={!selectedCity}
            onCityClick={handleCityClick}
            onBack={handleBackToCities}
            selectedCity={selectedCity}
          />
        </section>

        {/* AI Panel — only in city drill-down */}
        {selectedCity && <AiPanel apiBase={API_BASE} customRoutes={customRoutes} />}

        {/* Pathway AI Anomaly Insights — LLM explanations generated inside the Pathway pipeline */}
        {selectedCity && insights.length > 0 && (
          <section className="glass-card rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Pathway AI — Anomaly Insights
              <span className="text-xs text-slate-500 font-normal ml-auto">Auto-generated by LLM UDF in Pathway pipeline</span>
            </h3>
            <div className="space-y-2">
              {insights.slice(-5).reverse().map((insight, i) => (
                <div key={i} className="bg-slate-800/50 rounded-lg px-4 py-3 border border-cyan-500/10">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="w-2 h-2 rounded-full bg-cyan-400 flex-shrink-0"></span>
                    <span className="text-xs font-medium text-cyan-300">{insight.zone}</span>
                    <span className="text-xs text-slate-500">AQI {insight.aqi}</span>
                    {insight.zscore != null && insight.zscore !== 0 && (
                      <span className="text-xs text-amber-400">z={insight.zscore}</span>
                    )}
                    <span className="ml-auto text-xs text-slate-600">
                      {new Date(insight.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{insight.explanation}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Anomaly Alerts */}
        {anomalies.length > 0 && (
          <section className="glass-card rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              Recent Anomalies
            </h3>
            <div className="space-y-2">
              {anomalies.slice(-5).reverse().map((a, i) => (
                <div key={i} className="flex items-center gap-3 text-xs text-slate-400 bg-slate-800/50 rounded-lg px-3 py-2">
                  <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"></span>
                  <span className="font-medium text-amber-300">{a.zone}</span>
                  <span>AQI {a.aqi}</span>
                  {a.zscore != null && a.zscore !== 0 && <span className="text-amber-500">z-score: {a.zscore}</span>}
                  {a.type && <span className="text-slate-500 capitalize">{a.type}</span>}
                  <span className="ml-auto text-slate-500">
                    {new Date(a.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="text-center py-6 text-xs text-slate-600">
          RespiraRoute — Real-Time Urban Air Quality & Healthier Route Recommendations
          <br />
          Built with Pathway + FastAPI + React
        </footer>
      </main>
    </div>
  );
}

export default App;
