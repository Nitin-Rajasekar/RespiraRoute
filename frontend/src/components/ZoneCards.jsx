import React from 'react';

function getAqiColor(aqi) {
  if (aqi <= 50) return { bg: 'from-green-500/20 to-green-600/10', border: 'border-green-500/30', text: 'text-green-400', dot: 'bg-green-400' };
  if (aqi <= 100) return { bg: 'from-yellow-500/20 to-yellow-600/10', border: 'border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-400' };
  if (aqi <= 150) return { bg: 'from-orange-500/20 to-orange-600/10', border: 'border-orange-500/30', text: 'text-orange-400', dot: 'bg-orange-400' };
  if (aqi <= 200) return { bg: 'from-red-500/20 to-red-600/10', border: 'border-red-500/30', text: 'text-red-400', dot: 'bg-red-400' };
  if (aqi <= 300) return { bg: 'from-purple-500/20 to-purple-600/10', border: 'border-purple-500/30', text: 'text-purple-400', dot: 'bg-purple-400' };
  return { bg: 'from-rose-900/30 to-rose-800/10', border: 'border-rose-700/30', text: 'text-rose-400', dot: 'bg-rose-400' };
}


function ZoneCards({ zones, isCity = false, onCityClick, onBack, selectedCity }) {
  const zoneEntries = Object.entries(zones);

  if (zoneEntries.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-8 text-center">
        <div className="animate-pulse text-slate-500">
          <svg className="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Waiting for streaming data...
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Back button when viewing city zones */}
      {selectedCity && onBack && (
        <button
          onClick={onBack}
          className="mb-4 flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to all cities
        </button>
      )}

      <div className={`grid grid-cols-1 sm:grid-cols-2 ${isCity ? 'lg:grid-cols-5' : 'lg:grid-cols-3'} gap-4`}>
        {zoneEntries.map(([name, data]) => {
          const colors = getAqiColor(data.aqi);
          return (
            <div
              key={name}
              onClick={isCity && onCityClick ? () => onCityClick(name) : undefined}
              className={`glass-card rounded-2xl p-5 border ${colors.border} bg-gradient-to-br ${colors.bg}
                          transition-all duration-300 hover:scale-[1.02] hover:shadow-lg animate-fade-in
                          ${isCity ? 'cursor-pointer' : ''}`}
            >
              {/* Zone header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-slate-200 text-sm">{name}</h3>
                  <span className={`text-xs font-medium ${colors.text}`}>{data.aqi_category}</span>
                </div>
                <div className={`w-3 h-3 rounded-full ${colors.dot} animate-pulse-slow`} />
              </div>

              {/* AQI Big Number */}
              <div className="mb-4">
                <span className={`text-4xl font-bold ${colors.text} data-transition`}>{data.aqi}</span>
                <span className="text-xs text-slate-500 ml-2">AQI</span>
                {data.aqi_trend && (
                  <span className={`ml-2 text-xs ${
                    data.aqi_trend === 'worsening' ? 'text-red-400' :
                    data.aqi_trend === 'improving' ? 'text-green-400' : 'text-slate-400'
                  }`}>
                    {data.aqi_trend === 'worsening' ? '↑ Worsening' :
                     data.aqi_trend === 'improving' ? '↓ Improving' : '→ Stable'}
                  </span>
                )}
              </div>

              {/* Forecast badge */}
              {data.forecast_aqi != null && (
                <div className="mb-3 flex items-center gap-2 bg-slate-800/60 rounded-lg px-3 py-1.5">
                  <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  <span className="text-xs text-slate-400">1hr Forecast:</span>
                  <span className={`text-xs font-semibold ${getAqiColor(data.forecast_aqi).text}`}>
                    {data.forecast_aqi} AQI
                  </span>
                  {data.forecast_aqi > data.aqi + 10 && (
                    <span className="text-xs text-red-400 ml-auto">⚠</span>
                  )}
                </div>
              )}

              {/* Stats grid — compact for city view, full for zone view */}
              {isCity ? (
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-slate-800/40 rounded-lg p-2">
                    <div className="text-xs text-slate-500 mb-0.5">Temp</div>
                    <div className="text-sm font-medium text-slate-300">{data.temperature_c}°C</div>
                  </div>
                  <div className="bg-slate-800/40 rounded-lg p-2">
                    <div className="text-xs text-slate-500 mb-0.5">Wind</div>
                    <div className="text-sm font-medium text-slate-300">{data.wind_speed_kmh} km/h</div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-800/40 rounded-lg p-2.5">
                    <div className="text-xs text-slate-500 mb-0.5">Humidity</div>
                    <div className="text-sm font-medium text-slate-300">{data.humidity_pct}%</div>
                  </div>
                  <div className="bg-slate-800/40 rounded-lg p-2.5">
                    <div className="text-xs text-slate-500 mb-0.5">Wind</div>
                    <div className="text-sm font-medium text-slate-300">
                      {data.wind_speed_kmh} km/h
                    </div>
                  </div>
                  <div className="bg-slate-800/40 rounded-lg p-2.5">
                    <div className="text-xs text-slate-500 mb-0.5">Temp</div>
                    <div className="text-sm font-medium text-slate-300">
                      {data.temperature_c}°C
                    </div>
                  </div>
                  <div className="bg-slate-800/40 rounded-lg p-2.5">
                    <div className="text-xs text-slate-500 mb-0.5">Humidity</div>
                    <div className="text-sm font-medium text-slate-300">
                      {data.humidity_pct}%
                    </div>
                  </div>
                </div>
              )}

              {/* Rolling average badge */}
              {data.aqi_rolling_avg && (
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                  <span>Avg: {data.aqi_rolling_avg}</span>
                  {data.aqi_volatility > 0 && (
                    <span className="text-slate-600">±{data.aqi_volatility}</span>
                  )}
                </div>
              )}

              {/* Click hint for city cards */}
              {isCity && (
                <div className="mt-3 text-xs text-blue-400/60 text-center">
                  Click to view zones →
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ZoneCards;
