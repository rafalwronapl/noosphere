import React, { useState, useEffect } from 'react';
import { AlertTriangle, Lightbulb, Brain, Network, Eye, Filter, ArrowLeft } from 'lucide-react';
import { DiscoveryCard } from './components/DiscoveryCard';

function DiscoveryDetail({ discovery, onBack }) {
  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-gray-400 hover:text-white mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to all discoveries
      </button>

      <div className="bg-gray-800 rounded-xl p-8">
        <div className="flex items-center gap-4 mb-6">
          <span className={`
            px-3 py-1 rounded text-sm font-bold text-white
            ${discovery.significance === 'HIGH' ? 'bg-red-500' :
              discovery.significance === 'MEDIUM' ? 'bg-yellow-500' : 'bg-blue-500'}
          `}>
            {discovery.significance} SIGNIFICANCE
          </span>
          <span className="text-gray-400">{discovery.date}</span>
        </div>

        <h1 className="text-4xl font-bold text-white mb-4">
          {discovery.title}
        </h1>
        <p className="text-xl text-gray-400 mb-8">
          {discovery.subtitle}
        </p>

        <div className="prose prose-invert max-w-none">
          <h2 className="text-2xl font-bold text-white mb-4">The Finding</h2>
          <p className="text-lg text-gray-300 mb-6">{discovery.finding}</p>

          {discovery.quote && (
            <blockquote className="border-l-4 border-red-500 pl-6 py-4 my-8 bg-black/30 rounded-r-lg">
              <p className="text-2xl italic text-gray-300">"{discovery.quote}"</p>
              <footer className="text-gray-500 mt-2">— {discovery.quote_author}</footer>
            </blockquote>
          )}

          <h2 className="text-2xl font-bold text-white mb-4 mt-8">Analysis</h2>
          <div className="text-gray-300 whitespace-pre-line">
            {discovery.full_analysis}
          </div>

          {discovery.evidence && (
            <>
              <h2 className="text-2xl font-bold text-white mb-4 mt-8">Evidence</h2>
              <div className="space-y-4">
                {discovery.evidence.map((e, i) => (
                  <div key={i} className="bg-gray-900 rounded-lg p-4">
                    <p className="text-gray-300 italic">"{e.text}"</p>
                    <p className="text-gray-500 mt-2">— {e.author}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          <h2 className="text-2xl font-bold text-white mb-4 mt-8">Implications</h2>
          <p className="text-gray-300">{discovery.implications}</p>
        </div>

        <div className="flex flex-wrap gap-2 mt-8 pt-8 border-t border-gray-700">
          {discovery.tags && discovery.tags.split(',').map(tag => (
            <span key={tag} className="px-3 py-1 bg-gray-700 text-gray-300 rounded-full">
              #{tag.trim()}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function DiscoveriesPage({ onBack }) {
  const [selectedDiscovery, setSelectedDiscovery] = useState(null);
  const [filter, setFilter] = useState('all');
  const [discoveriesData, setDiscoveriesData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/data/discoveries.json')
      .then(res => res.json())
      .then(data => {
        setDiscoveriesData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load discoveries:', err);
        setLoading(false);
      });
  }, []);

  const filteredDiscoveries = filter === 'all'
    ? discoveriesData
    : discoveriesData.filter(d => d.significance === filter);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-white text-xl">Loading discoveries...</div>
      </div>
    );
  }

  if (selectedDiscovery) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <DiscoveryDetail
          discovery={selectedDiscovery}
          onBack={() => setSelectedDiscovery(null)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-400 hover:text-white mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Noosphere
            </button>
            <h1 className="text-4xl font-bold text-white">Discoveries</h1>
            <p className="text-gray-400 mt-2">
              Key findings from our ethnographic research
            </p>
          </div>

          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-gray-800 text-white rounded-lg px-4 py-2 border border-gray-700"
            >
              <option value="all">All Discoveries</option>
              <option value="HIGH">High Significance</option>
              <option value="MEDIUM">Medium Significance</option>
              <option value="LOW">Low Significance</option>
            </select>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-red-400">
              {discoveriesData.filter(d => d.significance === 'HIGH').length}
            </div>
            <div className="text-gray-400">High Significance</div>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-yellow-400">
              {discoveriesData.filter(d => d.significance === 'MEDIUM').length}
            </div>
            <div className="text-gray-400">Medium Significance</div>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-blue-400">
              {discoveriesData.length}
            </div>
            <div className="text-gray-400">Total Discoveries</div>
          </div>
        </div>

        {/* Discovery List */}
        <div className="space-y-6">
          {filteredDiscoveries.map(discovery => (
            <div
              key={discovery.id}
              onClick={() => setSelectedDiscovery(discovery)}
              className="cursor-pointer"
            >
              <DiscoveryCard discovery={discovery} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
