import React from 'react';

function HealthGauge({ routes, selectedRoute }) {
  const routeList = routes?.routes || [];
  const worstExposure = routeList.length > 0
    ? routeList[routeList.length - 1].total_exposure : 0;

  // Find the selected route (or fall back to recommended / first)
  const activeRoute = routeList.find(r => r.route_name === selectedRoute)
    || routeList.find(r => r.route_name === routes?.recommended)
    || routeList[0];

  // Compute health score from avg exposure per minute
  // Scale: 100 at <=50, 0 at >=500 (matches backend formula)
  const avgExp = activeRoute?.avg_exposure_per_minute || 0;
  const healthScore = Math.max(0, Math.min(100, Math.round(100 - (avgExp - 50) * 100 / 450)));

  // Savings compared to worst route
  const savingsPct = worstExposure > 0 && activeRoute
    ? Math.round((1 - activeRoute.total_exposure / worstExposure) * 1000) / 10
    : 0;

  const routeName = activeRoute?.route_name || '';

  const circumference = 2 * Math.PI * 54;
  const progress = (healthScore / 100) * circumference;
  const offset = circumference - progress;

  const getColor = (score) => {
    if (score >= 70) return { stroke: '#22c55e', text: 'text-green-400', label: 'Healthy', bg: 'from-green-500/10' };
    if (score >= 40) return { stroke: '#eab308', text: 'text-yellow-400', label: 'Moderate', bg: 'from-yellow-500/10' };
    return { stroke: '#ef4444', text: 'text-red-400', label: 'Unhealthy', bg: 'from-red-500/10' };
  };

  const colors = getColor(healthScore);

  return (
    <div className={`glass-card rounded-2xl p-6 h-full bg-gradient-to-br ${colors.bg} to-transparent`}>
      <h2 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
        <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
        Route Health Score
      </h2>

      <div className="flex flex-col items-center">
        {/* Circular gauge */}
        <div className="relative w-36 h-36 mb-4">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
            {/* Background circle */}
            <circle cx="60" cy="60" r="54" fill="none" stroke="#1e293b" strokeWidth="8" />
            {/* Progress circle */}
            <circle
              cx="60" cy="60" r="54" fill="none"
              stroke={colors.stroke}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="transition-all duration-1000 ease-out"
              style={{ filter: `drop-shadow(0 0 6px ${colors.stroke}40)` }}
            />
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${colors.text} data-transition`}>
              {healthScore}
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{colors.label}</span>
          </div>
        </div>

        {/* Stats */}
        <div className="w-full space-y-2">
          {savingsPct > 0 && (
            <div className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3 py-2">
              <span className="text-xs text-slate-500">vs Worst Route</span>
              <span className="text-sm font-semibold text-green-400">{savingsPct}% less exposure</span>
            </div>
          )}
          {routeName && (
            <div className="flex items-center justify-between bg-slate-800/40 rounded-lg px-3 py-2">
              <span className="text-xs text-slate-500">Viewing</span>
              <span className="text-xs font-medium text-blue-400 truncate ml-2">{routeName}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default HealthGauge;
