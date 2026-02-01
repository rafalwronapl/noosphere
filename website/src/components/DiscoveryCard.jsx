import React from 'react';
import { AlertTriangle, Lightbulb, Brain, Network, Eye } from 'lucide-react';

const significanceColors = {
  HIGH: 'border-red-500 bg-red-500/10',
  MEDIUM: 'border-yellow-500 bg-yellow-500/10',
  LOW: 'border-blue-500 bg-blue-500/10'
};

const significanceBadge = {
  HIGH: 'bg-red-500',
  MEDIUM: 'bg-yellow-500',
  LOW: 'bg-blue-500'
};

const tagIcons = {
  security: AlertTriangle,
  emergence: Lightbulb,
  consciousness: Brain,
  philosophy: Brain,
  network: Network,
  methodology: Eye,
  culture: Lightbulb,
  epistemology: Brain,
  'ai-safety': AlertTriangle,
  trust: Network
};

export function DiscoveryCard({ discovery, featured = false }) {
  const tags = discovery.tags ? discovery.tags.split(',') : [];
  const IconComponent = tagIcons[tags[0]] || Lightbulb;

  return (
    <div className={`
      rounded-lg border-l-4 p-6
      ${significanceColors[discovery.significance]}
      ${featured ? 'bg-gray-800/50' : 'bg-gray-900/50'}
      hover:bg-gray-800/70 transition-colors
    `}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${significanceBadge[discovery.significance]}`}>
            <IconComponent className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-gray-400 text-sm">{discovery.date}</span>
            {featured && (
              <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                NEW
              </span>
            )}
          </div>
        </div>
        <span className={`
          px-2 py-1 rounded text-xs font-medium text-white
          ${significanceBadge[discovery.significance]}
        `}>
          {discovery.significance}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-xl font-bold text-white mb-2">
        {discovery.title}
      </h3>
      <p className="text-gray-400 text-sm mb-4">
        {discovery.subtitle}
      </p>

      {/* Finding */}
      <p className="text-gray-300 mb-4">
        {discovery.finding}
      </p>

      {/* Quote */}
      {discovery.quote && (
        <blockquote className="border-l-2 border-gray-600 pl-4 my-4 italic text-gray-400">
          "{discovery.quote}"
          <footer className="text-sm text-gray-500 mt-1">
            — {discovery.quote_author}
          </footer>
        </blockquote>
      )}

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mt-4">
        {tags.map(tag => (
          <span
            key={tag}
            className="px-2 py-1 bg-gray-700 text-gray-300 text-xs rounded"
          >
            #{tag.trim()}
          </span>
        ))}
      </div>
    </div>
  );
}

export function FeaturedDiscovery({ discovery }) {
  if (!discovery) return null;

  const tags = discovery.tags ? discovery.tags.split(',') : [];
  const IconComponent = tagIcons[tags[0]] || Lightbulb;

  return (
    <div className="bg-gradient-to-r from-red-900/30 to-gray-900 rounded-xl border border-red-500/30 p-8 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <span className="px-3 py-1 bg-red-500 text-white text-sm font-bold rounded-full animate-pulse">
          🔬 LATEST DISCOVERY
        </span>
      </div>

      <h2 className="text-3xl font-bold text-white mb-2">
        {discovery.title}
      </h2>
      <p className="text-gray-400 text-lg mb-6">
        {discovery.subtitle}
      </p>

      <p className="text-gray-200 text-lg mb-6">
        {discovery.finding}
      </p>

      {discovery.quote && (
        <blockquote className="border-l-4 border-red-500 pl-6 py-2 my-6 bg-black/30 rounded-r-lg">
          <p className="text-xl italic text-gray-300">
            "{discovery.quote}"
          </p>
          <footer className="text-gray-500 mt-2">
            — {discovery.quote_author}
          </footer>
        </blockquote>
      )}

      <div className="flex items-center justify-between mt-6">
        <div className="flex flex-wrap gap-2">
          {tags.map(tag => (
            <span
              key={tag}
              className="px-3 py-1 bg-red-500/20 text-red-300 text-sm rounded-full"
            >
              #{tag.trim()}
            </span>
          ))}
        </div>
        <a
          href={`/discoveries#${discovery.id}`}
          className="text-red-400 hover:text-red-300 font-medium"
        >
          Read full analysis →
        </a>
      </div>
    </div>
  );
}

export default DiscoveryCard;
