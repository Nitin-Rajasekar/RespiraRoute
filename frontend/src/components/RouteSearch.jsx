import React, { useState, useCallback, useEffect, useRef } from 'react';
import LocationAutocomplete from './LocationAutocomplete';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const SEARCH_STEPS = [
  'Geocoding locations...',
  'Finding routes via OSRM...',
  'Sampling air quality along routes...',
  'Reverse geocoding area names...',
  'Calculating exposure scores...',
];

function RouteSearch({ onResults, onClear }) {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [startCoords, setStartCoords] = useState(null);
  const [endCoords, setEndCoords] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchStep, setSearchStep] = useState(0);
  const stepTimerRef = useRef(null);

  useEffect(() => {
    if (loading) {
      setSearchStep(0);
      let step = 0;
      stepTimerRef.current = setInterval(() => {
        step += 1;
        if (step < SEARCH_STEPS.length) {
          setSearchStep(step);
        }
      }, 3000);
    } else {
      if (stepTimerRef.current) clearInterval(stepTimerRef.current);
    }
    return () => { if (stepTimerRef.current) clearInterval(stepTimerRef.current); };
  }, [loading]);

  const doSearch = useCallback(async (startVal, endVal, sCoords, eCoords) => {
    if (!startVal.trim() || !endVal.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const startParam = sCoords ? `${sCoords.lat},${sCoords.lng}` : startVal.trim();
      const endParam = eCoords ? `${eCoords.lat},${eCoords.lng}` : endVal.trim();
      const params = new URLSearchParams({ start: startParam, end: endParam });
      const res = await fetch(`${API_BASE}/api/custom-routes?${params}`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else if (!data.routes || data.routes.length === 0) {
        setError(data.message || 'No routes found.');
      } else {
        data.start = startVal.trim();
        data.end = endVal.trim();
        onResults(data);
      }
    } catch (err) {
      setError('Failed to fetch routes. Check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, [onResults]);

  const handleSearch = async (e) => {
    e.preventDefault();
    doSearch(start, end, startCoords, endCoords);
  };

  const handleClear = () => {
    setStart('');
    setEnd('');
    setStartCoords(null);
    setEndCoords(null);
    setError(null);
    onClear();
  };

  return (
    <div className="glass-card rounded-2xl p-5">
      <h2 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
        <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        Route Search
      </h2>

      <form onSubmit={handleSearch} className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <LocationAutocomplete
            value={start}
            onChange={(val) => { setStart(val); setStartCoords(null); }}
            onSelect={(s) => setStartCoords({ lat: s.lat, lng: s.lng })}
            placeholder="Start — e.g. Connaught Place, New Delhi, India"
          />
          <LocationAutocomplete
            value={end}
            onChange={(val) => { setEnd(val); setEndCoords(null); }}
            onSelect={(s) => setEndCoords({ lat: s.lat, lng: s.lng })}
            placeholder="Destination — e.g. Dwarka Sector 21, New Delhi, India"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={loading || !start.trim() || !end.trim()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {SEARCH_STEPS[searchStep]}
              </>
            ) : (
              'Find Healthiest Route'
            )}
          </button>
          {(start || end) && (
            <button
              type="button"
              onClick={handleClear}
              className="px-3 py-2 text-slate-500 hover:text-slate-300 text-sm transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-red-400 text-xs">{error}</p>
        </div>
      )}
    </div>
  );
}

export default RouteSearch;
