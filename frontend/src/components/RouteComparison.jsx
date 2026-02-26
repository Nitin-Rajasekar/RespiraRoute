import React, { useState } from 'react';

const POLLUTANT_COLORS = {
  'PM2.5': { bar: 'bg-red-500', text: 'text-red-400' },
  'PM10':  { bar: 'bg-orange-500', text: 'text-orange-400' },
  'NO2':   { bar: 'bg-purple-500', text: 'text-purple-400' },
  'O3':    { bar: 'bg-cyan-500', text: 'text-cyan-400' },
  'CO':    { bar: 'bg-slate-400', text: 'text-slate-400' },
  'SO2':   { bar: 'bg-yellow-500', text: 'text-yellow-400' },
};

function RouteComparison({ routes, selectedRoute, onSelectRoute, onEnrichNames, enrichingNames }) {
  const routeList = routes?.routes || [];
  const recommended = routes?.recommended;
  const [expandedRoute, setExpandedRoute] = useState(null);

  if (routeList.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-6 h-full flex items-center justify-center">
        <p className="text-slate-500 text-sm animate-pulse">Computing routes...</p>
      </div>
    );
  }

  const maxExposure = Math.max(...routeList.map(r => r.total_exposure));
  // Find max value per pollutant across all routes for consistent bar scaling
  const maxPollutants = {};
  routeList.forEach(r => {
    if (r.pollutants) {
      Object.entries(r.pollutants).forEach(([k, v]) => {
        maxPollutants[k] = Math.max(maxPollutants[k] || 0, v);
      });
    }
  });

  return (
    <div className="glass-card rounded-2xl p-6 h-full">
      <h2 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
        <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        Route Comparison
        {onSelectRoute && (
          <span className="ml-auto text-[10px] text-slate-600 font-normal">Click a route to view on map</span>
        )}
      </h2>

      {(() => {
        const hasSegmentNames = routeList.some(r =>
          r.zone_details?.some(z => z.zone?.startsWith('Segment '))
        );
        return hasSegmentNames && onEnrichNames ? (
          <button
            onClick={onEnrichNames}
            disabled={enrichingNames}
            className="mb-4 flex items-center gap-2 px-4 py-2 rounded-xl text-sm
              bg-slate-800/50 border border-slate-700/30 text-slate-400
              hover:bg-slate-700/50 hover:text-slate-300 transition-all
              disabled:opacity-50 disabled:cursor-wait"
          >
            {enrichingNames ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-500 border-t-purple-400 rounded-full animate-spin" />
                Loading area names...
              </>
            ) : (
              <>📍 Load Area Names</>
            )}
          </button>
        ) : null;
      })()}

      <div className="space-y-4">
        {routeList.map((route, idx) => {
          const isRecommended = route.route_name === recommended;
          const isSelected = selectedRoute === route.route_name;
          const barWidth = (route.total_exposure / maxExposure) * 100;

          return (
            <div
              key={route.route_name}
              onClick={() => onSelectRoute && onSelectRoute(route.route_name)}
              className={`rounded-xl p-4 transition-all duration-300 ${
                onSelectRoute ? 'cursor-pointer hover:scale-[1.01]' : ''
              } ${
                isSelected
                  ? 'bg-blue-500/15 border-2 border-blue-400/50 shadow-lg shadow-blue-500/10'
                  : isRecommended
                    ? 'bg-green-500/10 border border-green-500/30 glow-green'
                    : 'bg-slate-800/30 border border-slate-700/20'
              }`}
            >
              {/* From → To */}
              {route.start && route.end && (
                <div className="flex items-center gap-2 mb-2 text-xs text-slate-500">
                  <svg className="w-3 h-3 text-green-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <circle cx="10" cy="10" r="4" />
                  </svg>
                  <span className="text-slate-400">{route.start}</span>
                  <svg className="w-3 h-3 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                  <svg className="w-3 h-3 text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <circle cx="10" cy="10" r="4" />
                  </svg>
                  <span className="text-slate-400">{route.end}</span>
                </div>
              )}

              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {isRecommended && (
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-bold rounded-full uppercase tracking-wider">
                      Recommended
                    </span>
                  )}
                  {isSelected && !isRecommended && (
                    <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-bold rounded-full uppercase tracking-wider">
                      Viewing
                    </span>
                  )}
                  <span className={`text-sm font-semibold ${
                    isSelected ? 'text-blue-300' : isRecommended ? 'text-green-300' : 'text-slate-300'
                  }`}>
                    {route.route_name}
                  </span>
                </div>
                <span className="text-xs text-slate-500">{route.total_time_minutes} min</span>
              </div>

              {/* Exposure bar */}
              <div className="relative h-2 bg-slate-700/50 rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${
                    isRecommended
                      ? 'bg-gradient-to-r from-green-500 to-green-400'
                      : idx === routeList.length - 1
                        ? 'bg-gradient-to-r from-red-600 to-red-400'
                        : 'bg-gradient-to-r from-yellow-600 to-yellow-400'
                  }`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>

              <div className="flex items-center justify-between">
                <span className={`text-lg font-bold data-transition ${
                  isRecommended ? 'text-green-400' : 'text-slate-300'
                }`}>
                  {route.total_exposure.toLocaleString()}
                </span>
                <span className="text-xs text-slate-500">exposure score</span>
              </div>

              {/* Zone breakdown */}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {route.zone_details.map((z, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-700/40 rounded text-[10px] text-slate-400"
                  >
                    {z.zone}
                    <span className={z.aqi > 150 ? 'text-red-400' : z.aqi > 100 ? 'text-yellow-400' : 'text-green-400'}>
                      {z.aqi}
                    </span>
                  </span>
                ))}
              </div>

              {/* Pollutant breakdown */}
              {route.pollutants && Object.keys(route.pollutants).length > 0 && (
                <div className="mt-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); setExpandedRoute(expandedRoute === route.route_name ? null : route.route_name); }}
                    className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
                  >
                    <svg className={`w-3 h-3 transition-transform ${expandedRoute === route.route_name ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    Pollutant Breakdown
                  </button>
                  {expandedRoute === route.route_name && (
                    <div className="mt-2 space-y-1.5 pl-1">
                      {Object.entries(route.pollutants).map(([name, value]) => {
                        const colors = POLLUTANT_COLORS[name] || { bar: 'bg-slate-500', text: 'text-slate-400' };
                        const maxVal = maxPollutants[name] || 1;
                        const barPct = Math.min(100, (value / maxVal) * 100);
                        return (
                          <div key={name} className="flex items-center gap-2">
                            <span className={`text-[10px] w-10 font-mono ${colors.text}`}>{name}</span>
                            <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${barPct}%` }} />
                            </div>
                            <span className="text-[10px] text-slate-500 w-12 text-right">{value}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RouteComparison;
