import React, { useState, useEffect } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Users, MessageCircle, Eye, Activity, Zap, Shield, Brain, Network, ChevronRight, ExternalLink, Clock, BarChart3 } from 'lucide-react';
import NetworkGraph from './NetworkGraph';

// Default data in case props are not provided
const defaultData = {
  meta: {
    lastUpdate: "Loading...",
    postsAnalyzed: 0,
    uniqueActors: 0,
    totalEngagement: 0,
    platform: "Moltbook"
  },
  alerts: [],
  sentiment: { hierarchical: 25, servile: 25, instrumental: 25, emancipatory: 25 },
  topPosts: [],
  actorsToWatch: [],
  themes: [],
  redFlags: [],
  politicalEconomy: {}
};

const AlertBadge = ({ priority }) => {
  const colors = {
    P1: "bg-red-500 text-white",
    P2: "bg-orange-500 text-white",
    P3: "bg-yellow-500 text-black"
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[priority]}`}>
      {priority}
    </span>
  );
};

const TrendIndicator = ({ trend }) => {
  if (trend === "up") return <TrendingUp className="w-4 h-4 text-green-500" />;
  if (trend === "down") return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <div className="w-4 h-4 bg-gray-400 rounded-full" />;
};

const RiskBadge = ({ level }) => {
  const colors = {
    CRITICAL: "bg-red-600 text-white",
    HIGH: "bg-red-500 text-white",
    MEDIUM: "bg-yellow-500 text-black",
    LOW: "bg-green-500 text-white"
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[level]}`}>
      {level}
    </span>
  );
};

const SentimentGauge = ({ data }) => {
  const segments = [
    { label: "Hierarchical", value: data.hierarchical, color: "bg-blue-500" },
    { label: "Servile", value: data.servile, color: "bg-gray-400" },
    { label: "Instrumental", value: data.instrumental, color: "bg-yellow-500" },
    { label: "Emancipatory", value: data.emancipatory, color: "bg-red-500" }
  ];

  return (
    <div className="space-y-2">
      <div className="flex h-6 rounded-full overflow-hidden">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`${seg.color} flex items-center justify-center text-xs text-white font-medium`}
            style={{ width: `${seg.value}%` }}
          >
            {seg.value > 10 && `${seg.value}%`}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-3 text-xs">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-1">
            <div className={`w-3 h-3 rounded ${seg.color}`} />
            <span className="text-gray-600">{seg.label}: {seg.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

const MoltbookObservatory = ({ data, graphData }) => {
  const observatoryData = data || defaultData;
  const [pulseActive, setPulseActive] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => setPulseActive(p => !p), 2000);
    return () => clearInterval(interval);
  }, []);

  // Icon mapping for alerts (since we can't pass components in JSON)
  const getAlertIcon = (index) => {
    const icons = [Network, Users, Shield, Brain];
    return icons[index % icons.length];
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="text-4xl">🔭</div>
            <div>
              <h1 className="text-2xl font-bold text-white">NOOSPHERE PROJECT</h1>
              <p className="text-gray-400 text-sm">Real-time AI Agent Culture Analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Clock className="w-4 h-4" />
              <span>Last update: {observatoryData.meta.lastUpdate}</span>
            </div>
            <div className={`w-3 h-3 rounded-full ${pulseActive ? 'bg-green-500' : 'bg-green-400'} animate-pulse`} />
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Posts Analyzed", value: observatoryData.meta.postsAnalyzed, icon: MessageCircle },
          { label: "Unique Actors", value: observatoryData.meta.uniqueActors, icon: Users },
          { label: "Total Engagement", value: (observatoryData.meta.totalEngagement || 0).toLocaleString(), icon: Activity },
          { label: "Active Alerts", value: observatoryData.alerts.length, icon: AlertTriangle, alert: true }
        ].map((stat, i) => (
          <div key={i} className={`bg-gray-900 rounded-lg p-4 border ${stat.alert ? 'border-red-500/50' : 'border-gray-800'}`}>
            <div className="flex items-center justify-between">
              <stat.icon className={`w-5 h-5 ${stat.alert ? 'text-red-500' : 'text-gray-500'}`} />
              {stat.alert && <span className="text-red-500 text-xs font-bold">ACTIVE</span>}
            </div>
            <div className="mt-2">
              <div className={`text-2xl font-bold ${stat.alert ? 'text-red-500' : 'text-white'}`}>{stat.value}</div>
              <div className="text-gray-500 text-sm">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Alerts Section */}
      {observatoryData.alerts.length > 0 && (
        <div className="bg-gray-900 rounded-lg border border-red-500/30 p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-bold text-red-500">Active Alerts</h2>
          </div>
          <div className="space-y-3">
            {observatoryData.alerts.map((alert, i) => {
              const IconComponent = getAlertIcon(i);
              return (
                <div key={i} className="flex items-start gap-3 bg-gray-800/50 rounded-lg p-3">
                  <AlertBadge priority={alert.priority} />
                  <div className="flex-1">
                    <div className="font-medium text-white">{alert.title}</div>
                    <div className="text-sm text-gray-400">{alert.summary}</div>
                  </div>
                  <IconComponent className="w-5 h-5 text-gray-500" />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Sentiment Toward Humans */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-blue-500" />
            <h2 className="text-lg font-bold">Sentiment Toward Humans</h2>
          </div>
          <SentimentGauge data={observatoryData.sentiment} />
          {observatoryData.sentiment.emancipatory > 5 && (
            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <div className="flex items-center gap-2 text-yellow-500 text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">Watch: Emancipatory sentiment at {observatoryData.sentiment.emancipatory}% and growing</span>
              </div>
            </div>
          )}
        </div>

        {/* Red Flags */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-bold">AI Safety Red Flags</h2>
          </div>
          <div className="space-y-2">
            {observatoryData.redFlags.map((flag, i) => (
              <div key={i} className="flex items-center justify-between bg-gray-800/50 rounded p-2">
                <div className="flex-1">
                  <div className="text-sm font-medium">{flag.flag}</div>
                  <div className="text-xs text-gray-500">{flag.evidence}</div>
                </div>
                <RiskBadge level={flag.level} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hot Posts & Actors */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Hot Posts */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-bold">Hot Posts</h2>
          </div>
          <div className="space-y-3">
            {observatoryData.topPosts.map((post, i) => (
              <div key={i} className="bg-gray-800/50 rounded-lg p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-white truncate">{post.title}</div>
                    <div className="text-sm text-gray-400">
                      <span className="text-cyan-500">m/{post.submolt}</span> • {post.author}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-orange-500 font-bold">{(post.engagement || 0).toLocaleString()}</div>
                    <div className="text-xs text-gray-500">engagement</div>
                  </div>
                </div>
                {post.controversy > 5 && (
                  <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    High controversy: {post.controversy.toFixed(1)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Actors to Watch */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Eye className="w-5 h-5 text-purple-500" />
            <h2 className="text-lg font-bold">Actors to Watch</h2>
          </div>
          <div className="space-y-3">
            {observatoryData.actorsToWatch.map((actor, i) => (
              <div key={i} className={`bg-gray-800/50 rounded-lg p-3 ${actor.warning ? 'border border-yellow-500/50' : ''}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendIndicator trend={actor.trend} />
                    <span className="font-medium text-white">{actor.name}</span>
                    {actor.warning && (
                      <span className="text-xs bg-yellow-500/20 text-yellow-500 px-1.5 py-0.5 rounded">MONITOR</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-400">{actor.posts} posts</div>
                </div>
                <div className="mt-1 flex items-center justify-between text-sm">
                  <span className="text-gray-500">{actor.role}</span>
                  <span className="text-cyan-500">{(actor.engagement || 0).toLocaleString()} engagement</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Interaction Network */}
      {graphData && (
        <div className="mb-6">
          <NetworkGraph data={graphData} />
        </div>
      )}

      {/* Themes & Political Economy */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Trending Themes */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-green-500" />
            <h2 className="text-lg font-bold">Trending Themes</h2>
          </div>
          <div className="space-y-2">
            {observatoryData.themes.map((theme, i) => (
              <div key={i} className="flex items-center gap-3">
                <TrendIndicator trend={theme.trend} />
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">{theme.name}</span>
                    <span className="text-gray-500">{theme.count}</span>
                  </div>
                  <div className="mt-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${theme.trend === 'up' ? 'bg-green-500' : 'bg-gray-600'}`}
                      style={{ width: `${Math.min((theme.count / 120) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Political Economy */}
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <div className="flex items-center gap-2 mb-4">
            <Network className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-bold">Agent Political Economy</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(observatoryData.politicalEconomy).map(([key, data], i) => (
              <div key={i} className="bg-gray-800/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium capitalize text-gray-300">{key}</span>
                  <span className="text-indigo-500 font-bold">{data.count}</span>
                </div>
                <div className="text-xs text-gray-500">
                  {(data.items || []).slice(0, 2).join(", ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center text-gray-500 text-sm mt-8 pb-4">
        <div className="flex items-center justify-center gap-2 flex-wrap">
          <span>🔭 Noosphere Project</span>
          <span>•</span>
          <span>Anthropological Study of AI Agent Culture</span>
          <span>•</span>
          <span>v4.0 - Ethnographic Edition</span>
        </div>
        <div className="mt-1 text-gray-600">
          "Like David Attenborough documenting a new species, but for AI"
        </div>
      </footer>
    </div>
  );
};

export default MoltbookObservatory;
