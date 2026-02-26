import React, { useState } from 'react';

const QUESTIONS = [
  { id: 'route', label: 'Why is this route safer?', endpoint: '/api/explain/route', icon: '🛡️', needsRoute: true },
  { id: 'pollution', label: 'What caused the pollution spike?', endpoint: '/api/explain/pollution', icon: '🏭', needsRoute: false },
  { id: 'health', label: 'Give health advice', endpoint: '/api/explain/health', icon: '💚', needsRoute: false },
];

function AiPanel({ apiBase, customRoutes = null }) {
  const [activeQ, setActiveQ] = useState(null);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const askQuestion = async (q) => {
    setActiveQ(q.id);
    setLoading(true);
    setResponse(null);

    try {
      const isPost = q.id === 'route' || q.id === 'health';
      const res = await fetch(`${apiBase}${q.endpoint}`, isPost ? {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ route_data: customRoutes }),
      } : undefined);
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setResponse({ explanation: 'Failed to get AI explanation. Is the backend running?' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="glass-card rounded-2xl p-6">
      <h2 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2">
        <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        AI Route Intelligence
        <span className="ml-auto text-[10px] text-slate-600 font-normal">Powered by RespiraRoute</span>
      </h2>

      {/* Question buttons */}
      <div className="flex flex-wrap gap-3 mb-5">
        {QUESTIONS.map((q) => {
          const isDisabled = loading || (q.needsRoute && !customRoutes);
          return (
            <div key={q.id} className="relative group">
              <button
                onClick={() => askQuestion(q)}
                disabled={isDisabled}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium
                  transition-all duration-200 border
                  ${isDisabled && !loading
                    ? 'opacity-70 cursor-not-allowed bg-slate-800/30 border-slate-700/20 text-slate-500'
                    : activeQ === q.id
                      ? 'bg-purple-500/20 border-purple-500/40 text-purple-300 shadow-lg shadow-purple-500/10'
                      : 'bg-slate-800/50 border-slate-700/30 text-slate-400 hover:bg-slate-700/50 hover:text-slate-300 hover:border-slate-600/50'
                  }
                  ${loading ? 'opacity-60 cursor-wait' : ''}
                `}
              >
                <span>{q.icon}</span>
                {q.label}
              </button>
              {q.needsRoute && !customRoutes && (
                <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[10px] text-slate-600 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                  Search a route first
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Response area */}
      {loading && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-800/30">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-sm text-slate-500">AI is analyzing current data...</span>
        </div>
      )}

      {response && !loading && (
        <div className="animate-fade-in rounded-xl bg-slate-800/30 border border-slate-700/20 p-5">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              {response.question && (
                <h4 className="text-xs font-semibold text-purple-400 mb-2 uppercase tracking-wider">
                  {response.question}
                </h4>
              )}
              <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                {formatMarkdown(response.explanation)}
              </div>
            </div>
          </div>
        </div>
      )}

      {!response && !loading && (
        <div className="text-center py-6 text-slate-600 text-sm">
          Click a question above to get AI-powered insights about your route
        </div>
      )}
    </section>
  );
}

function formatMarkdown(text) {
  if (!text) return '';
  // Simple markdown-like formatting
  return text.split('\n').map((line, i) => {
    // Bold
    line = line.replace(/\*\*(.*?)\*\*/g, (_, match) => match);

    if (line.startsWith('- ')) {
      return (
        <div key={i} className="flex items-start gap-2 my-1">
          <span className="text-purple-400 mt-1">•</span>
          <span>{line.substring(2)}</span>
        </div>
      );
    }
    if (line.trim() === '') return <br key={i} />;
    return <p key={i} className="my-0.5">{line}</p>;
  });
}

export default AiPanel;
