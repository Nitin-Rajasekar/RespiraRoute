import React from 'react';

function Header({ connected, lastUpdate }) {
  return (
    <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-blue-500 flex items-center justify-center shadow-lg shadow-green-500/20">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold gradient-text">RespiraRoute</h1>
            <p className="text-xs text-slate-500">Real-Time Air Quality & Route Intelligence</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Live indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
            <div className={`live-dot ${!connected ? 'bg-red-500' : ''}`}
                 style={!connected ? { background: '#ef4444' } : {}} />
            <span className="text-xs font-medium text-slate-400">
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>

          {lastUpdate && (
            <span className="text-xs text-slate-600 hidden sm:block">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
