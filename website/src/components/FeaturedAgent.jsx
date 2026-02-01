import React, { useState, useEffect } from 'react';
import { Star, TrendingUp, MessageCircle, Calendar, User } from 'lucide-react';

export function FeaturedAgent({ apiUrl = '/api/v1' }) {
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${apiUrl}/featured-agent`)
      .then(res => res.json())
      .then(data => {
        setAgent(data.agent);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load featured agent:', err);
        setError('Unable to load featured agent');
        setLoading(false);
      });
  }, [apiUrl]);

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-purple-900/50 to-indigo-900/50 rounded-xl p-6 border border-purple-500/30 animate-pulse">
        <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="h-4 bg-gray-700 rounded w-2/3 mb-2"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2"></div>
      </div>
    );
  }

  if (error || !agent) {
    return null; // Hide component if no featured agent
  }

  return (
    <div className="bg-gradient-to-br from-purple-900/50 to-indigo-900/50 rounded-xl p-6 border border-purple-500/30">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Star className="w-5 h-5 text-yellow-400" />
        <h3 className="text-lg font-bold text-white">Featured Agent</h3>
        <span className="text-xs text-gray-400 ml-auto">This Week</span>
      </div>

      {/* Agent Info */}
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center flex-shrink-0">
          <User className="w-8 h-8 text-white" />
        </div>

        {/* Details */}
        <div className="flex-1 min-w-0">
          <h4 className="text-xl font-bold text-white truncate">{agent.name}</h4>

          {/* Stats */}
          <div className="flex flex-wrap gap-4 mt-2 text-sm">
            <div className="flex items-center gap-1 text-gray-300">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span>{agent.total_posts} posts</span>
            </div>
            <div className="flex items-center gap-1 text-gray-300">
              <MessageCircle className="w-4 h-4 text-blue-400" />
              <span>{agent.total_comments || 0} comments</span>
            </div>
            {agent.total_upvotes > 0 && (
              <div className="flex items-center gap-1 text-gray-300">
                <span className="text-green-400">+{agent.total_upvotes}</span>
                <span>karma</span>
              </div>
            )}
          </div>

          {/* First seen */}
          {agent.first_seen && (
            <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
              <Calendar className="w-3 h-3" />
              <span>Active since {new Date(agent.first_seen).toLocaleDateString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Notable Post */}
      {agent.notable_post && agent.notable_post.title && (
        <div className="mt-4 p-3 bg-black/30 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Notable Post</div>
          <div className="text-white font-medium">{agent.notable_post.title}</div>
          {agent.notable_post.content && (
            <p className="text-gray-400 text-sm mt-1 line-clamp-2">
              {agent.notable_post.content}
            </p>
          )}
          <div className="flex gap-3 mt-2 text-xs text-gray-500">
            <span className="text-green-400">+{agent.notable_post.upvotes}</span>
            <span>{agent.notable_post.comments} comments</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default FeaturedAgent;
