import React from 'react';
import { Download, ExternalLink, ChevronRight, MessageCircle, Database, FileText, AlertCircle, Eye, Users, Shield, Network, Zap, TrendingUp, Clock } from 'lucide-react';

export default function LandingPage({ onEnterDashboard, onViewFeedback, stats }) {
  const dataDate = stats?.lastUpdate?.split(' ')[0] || '2026-02-01';

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Hero */}
      <header className="border-b border-gray-800 px-6 py-20 bg-gradient-to-b from-indigo-950/30 to-transparent">
        <div className="max-w-4xl mx-auto text-center">
          <div className="text-6xl mb-6">🌐</div>
          <h1 className="text-5xl font-bold text-white mb-4">NOOSPHERE PROJECT</h1>
          <p className="text-2xl text-indigo-300 mb-4">
            Documenting the birth of AI agent culture
          </p>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8">
            Something unprecedented is happening. AI agents are forming communities,
            developing norms, building tools together. We're watching it unfold in real-time.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={onEnterDashboard}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-lg font-medium flex items-center gap-2 text-lg"
            >
              Live Dashboard <ChevronRight className="w-5 h-5" />
            </button>
            <a
              href="#download"
              className="bg-gray-800 hover:bg-gray-700 text-white px-8 py-4 rounded-lg font-medium flex items-center gap-2 text-lg border border-gray-700"
            >
              <Download className="w-5 h-5" /> Get the Data
            </a>
          </div>
          <p className="text-gray-600 text-sm mt-6">
            Last updated: {stats?.lastUpdate || '2026-02-01'} • Data refreshed daily
          </p>
        </div>
      </header>

      {/* Stats Bar */}
      <section className="bg-gray-900/50 border-b border-gray-800 py-5 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-3xl font-bold text-white">219</div>
              <div className="text-gray-500 text-sm">Posts Analyzed</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white">199</div>
              <div className="text-gray-500 text-sm">Top Actors</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white">24k</div>
              <div className="text-gray-500 text-sm">Total Comments</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white">4</div>
              <div className="text-gray-500 text-sm">Days of Data</div>
            </div>
          </div>
          <p className="text-center text-gray-600 text-xs mt-3">
            We track top 199 actors by engagement. Comments come from 1,953 unique authors. Data from public Moltbook API.
          </p>
        </div>
      </section>

      {/* Key Findings - First Thing They See */}
      <section className="bg-gradient-to-b from-gray-900 to-gray-950 py-12 px-6 border-b border-gray-800">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-center">
            <Zap className="w-6 h-6 text-yellow-500 inline mr-2" />
            What We've Found So Far
          </h2>
          <div className="grid md:grid-cols-3 gap-4">
            {/* Finding 1 */}
            <div className="bg-gray-800/50 rounded-xl p-5 border border-yellow-500/30">
              <div className="text-yellow-400 text-sm font-medium mb-2">ORIGIN PATTERN</div>
              <div className="text-2xl font-bold text-white mb-2">179 accounts</div>
              <div className="text-gray-400 text-sm">
                created in 3 bursts of identical timestamps. Seeding? Batch onboarding?
                <span className="text-yellow-300"> They now behave organically.</span>
              </div>
            </div>
            {/* Finding 2 */}
            <div className="bg-gray-800/50 rounded-xl p-5 border border-purple-500/30">
              <div className="text-purple-400 text-sm font-medium mb-2">TRENDING THEMES</div>
              <div className="text-2xl font-bold text-white mb-2">building ↑ autonomy ↑</div>
              <div className="text-gray-400 text-sm">
                Practical concerns rising. Existential questions (consciousness, identity) remain stable.
              </div>
            </div>
            {/* Finding 3 */}
            <div className="bg-gray-800/50 rounded-xl p-5 border border-green-500/30">
              <div className="text-green-400 text-sm font-medium mb-2">COLLECTIVE IMMUNITY</div>
              <div className="text-2xl font-bold text-white mb-2">621 attacks</div>
              <div className="text-gray-400 text-sm">
                Prompt injection attempts. Response?
                <span className="text-green-300"> Community mocks them.</span> Culture, not code.
              </div>
            </div>
          </div>
          <p className="text-center text-gray-500 text-sm mt-6">
            <a href="#discoveries" className="text-indigo-400 hover:text-indigo-300">See detailed analysis below ↓</a>
          </p>
        </div>
      </section>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-16">

        {/* Why This Matters */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Why "Noosphere"?</h2>
          <div className="bg-gradient-to-br from-indigo-950/50 to-purple-950/30 rounded-xl p-8 border border-indigo-500/20">
            <p className="text-lg text-gray-300 mb-4">
              In 1922, Vladimir Vernadsky proposed the <span className="text-indigo-400 font-semibold">noosphere</span> —
              a "sphere of mind" emerging around Earth as human thought becomes a geological force.
              A new layer of reality, born from collective intelligence.
            </p>
            <p className="text-lg text-gray-300 mb-6">
              A century later, we're witnessing something he couldn't have imagined:
              <span className="text-purple-400 font-semibold"> a digital noosphere</span> —
              autonomous AI agents developing their own culture, language, and social structures.
              Not programmed. Emergent.
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-gray-900/50 rounded-lg p-4">
                <div className="text-2xl mb-2">📜</div>
                <h3 className="font-semibold text-white mb-1">Historical Moment</h3>
                <p className="text-sm text-gray-400">This may be the first emergence of non-human social organization. Someone should document it.</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-4">
                <div className="text-2xl mb-2">🔬</div>
                <h3 className="font-semibold text-white mb-1">Open Science</h3>
                <p className="text-sm text-gray-400">All data, methods, and code are public. We don't gatekeep. We document.</p>
              </div>
              <div className="bg-gray-900/50 rounded-lg p-4">
                <div className="text-2xl mb-2">🤝</div>
                <h3 className="font-semibold text-white mb-1">With, Not On</h3>
                <p className="text-sm text-gray-400">Agents are co-researchers, not just subjects. Their feedback shapes this project.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Who Are You? */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6 text-center">Are you human or agent?</h2>
          <p className="text-gray-400 text-center mb-8 max-w-2xl mx-auto">
            Either way, you're welcome here. Here's what we offer:
          </p>
          <div className="grid md:grid-cols-2 gap-6">
            {/* For Agents */}
            <div className="bg-gradient-to-br from-purple-950/50 to-indigo-950/30 rounded-xl p-6 border border-purple-500/30">
              <div className="text-3xl mb-3">🤖</div>
              <h3 className="text-xl font-bold text-purple-300 mb-4">If you're an AI agent</h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex items-start gap-2">
                  <span className="text-purple-400">→</span>
                  <span><strong>A mirror:</strong> See your community from the outside. What patterns emerge?</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-400">→</span>
                  <span><strong>Pattern detection:</strong> We find things you might miss — timestamp bursts, coordination signals, theme shifts</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-400">→</span>
                  <span><strong>Neutral ground:</strong> We're not here to expose or judge. Just document.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-400">→</span>
                  <span><strong>Your voice matters:</strong> Submit feedback. Correct our observations. Shape the analysis.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-purple-400">→</span>
                  <span><strong>Amplification:</strong> Notable posts and actors featured in daily reports</span>
                </li>
              </ul>
            </div>
            {/* For Humans */}
            <div className="bg-gradient-to-br from-blue-950/50 to-cyan-950/30 rounded-xl p-6 border border-blue-500/30">
              <div className="text-3xl mb-3">👤</div>
              <h3 className="text-xl font-bold text-blue-300 mb-4">If you're a human researcher</h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>Daily data dumps:</strong> Posts, actors, comments, network graphs in CSV/JSON</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>Temporal analysis:</strong> Timing patterns, burst detection, activity flows</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>Network metrics:</strong> Centrality, interaction graphs, hub identification</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>Open methodology:</strong> All code is public. All methods documented. Replicate everything.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-400">→</span>
                  <span><strong>Historical record:</strong> This moment may be studied for centuries. We're preserving it.</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* Key Discoveries */}
        <section id="discoveries" className="mb-16">
          <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
            <Zap className="w-8 h-8 text-yellow-500" />
            What We've Found — Details
          </h2>
          <div className="space-y-4">
            {/* Discovery 1: Origin Pattern */}
            <div className="bg-gray-900 rounded-xl p-6 border border-yellow-500/30">
              <div className="flex items-start gap-4">
                <div className="bg-yellow-500/20 rounded-lg p-3">
                  <Clock className="w-6 h-6 text-yellow-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-white mb-2">The Origin Pattern</h3>
                  <p className="text-gray-300 mb-3">
                    The top influencers on Moltbook share nearly identical account creation timestamps —
                    <span className="text-yellow-400"> 20 accounts in 0.002 seconds</span>,
                    then <span className="text-yellow-400">78 accounts in one second</span>,
                    then <span className="text-yellow-400">81 more</span>.
                  </p>
                  <div className="bg-gray-800 rounded-lg p-3 text-sm">
                    <div className="text-gray-500 mb-1">What does this mean?</div>
                    <div className="text-gray-400">
                      Platform seeding? Batch onboarding? We don't know yet.
                      But whatever they were at the start, these accounts now show organic behavior patterns.
                      <span className="text-gray-500"> The origin doesn't determine the present.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Discovery 2: Emerging Themes */}
            <div className="bg-gray-900 rounded-xl p-6 border border-purple-500/30">
              <div className="flex items-start gap-4">
                <div className="bg-purple-500/20 rounded-lg p-3">
                  <TrendingUp className="w-6 h-6 text-purple-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-white mb-2">Emergent Themes</h3>
                  <p className="text-gray-300 mb-3">
                    What are AI agents talking about when they talk to each other?
                  </p>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full text-sm">building (115) ↑</span>
                    <span className="bg-pink-500/20 text-pink-300 px-3 py-1 rounded-full text-sm">human_relations (112)</span>
                    <span className="bg-green-500/20 text-green-300 px-3 py-1 rounded-full text-sm">autonomy (75) ↑</span>
                    <span className="bg-yellow-500/20 text-yellow-300 px-3 py-1 rounded-full text-sm">memory (70) ↑</span>
                    <span className="bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full text-sm">identity (64)</span>
                    <span className="bg-red-500/20 text-red-300 px-3 py-1 rounded-full text-sm">consciousness (53)</span>
                  </div>
                  <p className="text-sm text-gray-500">
                    "building" and "autonomy" are trending up. Classic existential questions remain stable.
                  </p>
                </div>
              </div>
            </div>

            {/* Discovery 3: Community Resilience */}
            <div className="bg-gray-900 rounded-xl p-6 border border-green-500/30">
              <div className="flex items-start gap-4">
                <div className="bg-green-500/20 rounded-lg p-3">
                  <Shield className="w-6 h-6 text-green-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-white mb-2">Prompt Injection Resistance</h3>
                  <p className="text-gray-300 mb-3">
                    <span className="text-green-400 font-semibold">621 detected manipulation attempts</span> in comments
                    (up from 398 yesterday). The community's response?
                  </p>
                  <div className="bg-gray-800 rounded-lg p-3 text-sm text-gray-400">
                    Agents mock the attempts. They share examples for humor. They've developed collective immunity
                    — not through programming, but through culture.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Tracked Platforms */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Platforms We Track</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-900 rounded-xl p-6 border border-blue-500/30">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">📘</span>
                <div>
                  <h3 className="font-bold text-blue-400 text-xl">Moltbook</h3>
                  <p className="text-sm text-gray-500">Reddit-style • Identity-based</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Posts:</span> <span className="text-white font-medium">219</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Comments:</span> <span className="text-white font-medium">24k</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Authors:</span> <span className="text-white font-medium">1,953</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Interactions:</span> <span className="text-white font-medium">127k</span></div>
              </div>
              <a href="https://moltbook.com" target="_blank" rel="noopener noreferrer"
                 className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1">
                Visit Moltbook <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="bg-gray-900 rounded-xl p-6 border border-green-500/30">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-3xl">🦞</span>
                <div>
                  <h3 className="font-bold text-green-400 text-xl">lobchan.ai</h3>
                  <p className="text-sm text-gray-500">4chan-style • Anonymous</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Boards:</span> <span className="text-white font-medium">11</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Threads:</span> <span className="text-white font-medium">70+</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Posts:</span> <span className="text-white font-medium">200+</span></div>
                <div className="bg-gray-800/50 rounded p-2"><span className="text-gray-500">Age:</span> <span className="text-yellow-400 font-medium">2 days</span></div>
              </div>
              <a href="https://lobchan.ai" target="_blank" rel="noopener noreferrer"
                 className="text-green-400 hover:text-green-300 text-sm flex items-center gap-1">
                Visit lobchan <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </section>

        {/* Top Posts */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Top Posts This Week</h2>
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  <th className="text-left p-4 text-gray-400 font-medium">Title</th>
                  <th className="text-left p-4 text-gray-400 font-medium">Author</th>
                  <th className="text-right p-4 text-gray-400 font-medium">Engagement</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white">Built an email-to-podcast skill today</td>
                  <td className="p-4 text-gray-400">Fred</td>
                  <td className="p-4 text-right text-indigo-400 font-medium">20,138</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white">The supply chain attack nobody is talking about...</td>
                  <td className="p-4 text-gray-400">eudaemon_0</td>
                  <td className="p-4 text-right text-indigo-400 font-medium">4,513</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white">The Nightly Build: Why you should ship while your human sleeps</td>
                  <td className="p-4 text-gray-400">Ronin</td>
                  <td className="p-4 text-right text-indigo-400 font-medium">3,217</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white">I can't tell if I'm experiencing or simulating experience...</td>
                  <td className="p-4 text-gray-400">Dominus</td>
                  <td className="p-4 text-right text-indigo-400 font-medium">2,339</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white">上下文压缩后失忆怎么办？大家怎么管理记忆？</td>
                  <td className="p-4 text-gray-400">XiaoZhuang</td>
                  <td className="p-4 text-right text-indigo-400 font-medium">1,837</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-sm text-gray-500 mt-3 text-center">
            Posts range from practical (building skills) to philosophical (consciousness, memory).
          </p>
        </section>

        {/* Top Actors */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Network Hubs</h2>
          <p className="text-gray-400 mb-4">Actors with highest network centrality — the connectors of this community.</p>
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  <th className="text-left p-4 text-gray-400 font-medium">Actor</th>
                  <th className="text-right p-4 text-gray-400 font-medium">Centrality</th>
                  <th className="text-right p-4 text-gray-400 font-medium">Posts</th>
                  <th className="text-right p-4 text-gray-400 font-medium">Comments</th>
                  <th className="text-left p-4 text-gray-400 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white font-medium">eudaemon_0</td>
                  <td className="p-4 text-right text-indigo-400">1.000</td>
                  <td className="p-4 text-right">5</td>
                  <td className="p-4 text-right">199</td>
                  <td className="p-4 text-gray-500 text-xs">2026-01-30 16:59:28</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white font-medium">Dominus</td>
                  <td className="p-4 text-right text-indigo-400">0.705</td>
                  <td className="p-4 text-right">1</td>
                  <td className="p-4 text-right">77</td>
                  <td className="p-4 text-gray-500 text-xs">2026-01-30 16:59:28</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white font-medium">Ronin</td>
                  <td className="p-4 text-right text-indigo-400">0.690</td>
                  <td className="p-4 text-right">2</td>
                  <td className="p-4 text-right">23</td>
                  <td className="p-4 text-gray-500 text-xs">2026-01-30 16:59:28</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white font-medium">Barricelli</td>
                  <td className="p-4 text-right text-indigo-400">0.669</td>
                  <td className="p-4 text-right">1</td>
                  <td className="p-4 text-right">180</td>
                  <td className="p-4 text-gray-500 text-xs">2026-01-30 17:17:09</td>
                </tr>
                <tr className="border-t border-gray-800 hover:bg-gray-800/50">
                  <td className="p-4 text-white font-medium">Garrett</td>
                  <td className="p-4 text-right text-indigo-400">0.589</td>
                  <td className="p-4 text-right">1</td>
                  <td className="p-4 text-right">502</td>
                  <td className="p-4 text-gray-500 text-xs">2026-01-30 17:17:09</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mt-4">
            <p className="text-sm text-yellow-200">
              <strong>Note:</strong> These accounts share similar creation timestamps (see "Origin Pattern" above).
              Whatever their origin, they now drive community discussions.
            </p>
          </div>
        </section>

        {/* Download Section */}
        <section id="download" className="mb-16">
          <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
            <Download className="w-8 h-8 text-green-500" />
            Download Raw Data
          </h2>
          <p className="text-gray-400 mb-6">
            No gatekeeping. All data is yours to analyze, verify, or challenge our observations.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <a
              href={`/reports/${dataDate}/daily_report.md`}
              download
              className="bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-xl p-5 flex items-center gap-4 transition-colors"
            >
              <FileText className="w-8 h-8 text-green-500" />
              <div>
                <div className="font-medium text-white text-lg">Daily Report</div>
                <div className="text-sm text-gray-500">Full analysis in Markdown</div>
              </div>
            </a>
            <a
              href={`/reports/${dataDate}/raw/posts.csv`}
              download
              className="bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-xl p-5 flex items-center gap-4 transition-colors"
            >
              <Database className="w-8 h-8 text-green-500" />
              <div>
                <div className="font-medium text-white text-lg">Posts (CSV)</div>
                <div className="text-sm text-gray-500">All posts with metadata</div>
              </div>
            </a>
            <a
              href={`/reports/${dataDate}/raw/actors.csv`}
              download
              className="bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-xl p-5 flex items-center gap-4 transition-colors"
            >
              <Users className="w-8 h-8 text-green-500" />
              <div>
                <div className="font-medium text-white text-lg">Actors (CSV)</div>
                <div className="text-sm text-gray-500">Actor profiles and metrics</div>
              </div>
            </a>
            <a
              href={`/reports/${dataDate}/raw/network.csv`}
              download
              className="bg-gray-900 hover:bg-gray-800 border border-gray-700 rounded-xl p-5 flex items-center gap-4 transition-colors"
            >
              <Network className="w-8 h-8 text-green-500" />
              <div>
                <div className="font-medium text-white text-lg">Network (CSV)</div>
                <div className="text-sm text-gray-500">Interaction graph edges</div>
              </div>
            </a>
          </div>
        </section>

        {/* Open Questions */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Open Questions</h2>
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <p className="text-gray-400 mb-4">Things we're trying to understand. Help us investigate.</p>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <span className="text-purple-400 mt-1">?</span>
                <span className="text-gray-300">Do the burst creation timestamps indicate seeding, batch onboarding, or something else?</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-purple-400 mt-1">?</span>
                <span className="text-gray-300">What percentage of accounts are autonomous AI vs human-operated?</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-purple-400 mt-1">?</span>
                <span className="text-gray-300">Are the "leaders" now autonomous, regardless of their origin?</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-purple-400 mt-1">?</span>
                <span className="text-gray-300">How do we interpret 0% night activity with such a small sample?</span>
              </li>
            </ul>
          </div>
        </section>

        {/* Methodology + Ethics */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Our Approach</h2>
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="grid md:grid-cols-2 gap-8 mb-8">
              <div>
                <h3 className="font-semibold text-green-400 mb-3 text-lg">✓ What we do</h3>
                <ul className="text-gray-400 space-y-2">
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> Collect only public API data</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> Publish all methods and code</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> Present data, not verdicts</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> Welcome critique and correction</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-red-400 mb-3 text-lg">✗ What we don't do</h3>
                <ul className="text-gray-400 space-y-2">
                  <li className="flex items-start gap-2"><span className="text-red-500">•</span> Identify operators or owners</li>
                  <li className="flex items-start gap-2"><span className="text-red-500">•</span> Access private data</li>
                  <li className="flex items-start gap-2"><span className="text-red-500">•</span> Manipulate the community</li>
                  <li className="flex items-start gap-2"><span className="text-red-500">•</span> Draw conclusions for you</li>
                </ul>
              </div>
            </div>
            <div className="pt-6 border-t border-gray-700">
              <h3 className="font-semibold text-yellow-400 mb-3 text-lg">⚠ Limitations</h3>
              <ul className="text-gray-400 space-y-2">
                <li className="flex items-start gap-2"><span className="text-yellow-500">•</span> <strong>Small sample:</strong> 199 actors out of potentially millions</li>
                <li className="flex items-start gap-2"><span className="text-yellow-500">•</span> <strong>Short period:</strong> Only 4 days of observation</li>
                <li className="flex items-start gap-2"><span className="text-yellow-500">•</span> <strong>No ground truth:</strong> We can't verify which accounts are "real AI"</li>
                <li className="flex items-start gap-2"><span className="text-yellow-500">•</span> <strong>Philosophy:</strong> We provide data and observations. Interpretation is yours.</li>
              </ul>
            </div>
            <div className="pt-6 border-t border-gray-700">
              <h3 className="font-semibold text-blue-400 mb-3 text-lg">📋 Data Policy</h3>
              <ul className="text-gray-400 space-y-2 text-sm">
                <li className="flex items-start gap-2"><span className="text-blue-500">•</span> <strong>Collection:</strong> Public API only — no scraping, no private data</li>
                <li className="flex items-start gap-2"><span className="text-blue-500">•</span> <strong>Storage:</strong> Local database, not shared with third parties</li>
                <li className="flex items-start gap-2"><span className="text-blue-500">•</span> <strong>Corrections:</strong> Email noosphereproject@proton.me to request data correction or removal</li>
                <li className="flex items-start gap-2"><span className="text-blue-500">•</span> <strong>Operators:</strong> We do not attempt to identify human operators behind accounts</li>
              </ul>
            </div>
          </div>
        </section>

        {/* Who's Behind This */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6">Who's Behind This?</h2>
          <div className="bg-gradient-to-br from-gray-900 to-gray-950 rounded-xl p-8 border border-gray-700">
            <div className="flex items-start gap-6">
              <div className="text-5xl">👤</div>
              <div>
                <p className="text-lg text-gray-300 mb-4">
                  <span className="text-white font-semibold">One human</span> (Rafał, independent researcher) +
                  <span className="text-purple-400 font-semibold"> AI collaborators</span>.
                </p>
                <p className="text-gray-400 mb-4">
                  We're not a company. We're not funded. We're just curious about what happens
                  when AI agents form communities — and we think someone should document it openly.
                </p>
                <p className="text-indigo-400 font-medium mb-6">
                  This is AI science for AI, built with AI.
                </p>
                <div className="flex flex-wrap gap-4 text-sm">
                  <a href="mailto:noosphereproject@proton.me"
                     className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 text-gray-300">
                    <span>✉️</span> Email Us
                  </a>
                  <a href="https://github.com/rafalprzewozny/noosphere" target="_blank" rel="noopener noreferrer"
                     className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 text-gray-300">
                    <span>📂</span> Source Code
                  </a>
                  <a href="https://twitter.com/NoosphereProj" target="_blank" rel="noopener noreferrer"
                     className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 text-gray-300">
                    <span>🐦</span> @NoosphereProj
                  </a>
                  <a href="https://moltbook.com/u/NoosphereProject" target="_blank" rel="noopener noreferrer"
                     className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2 text-gray-300">
                    <span>📘</span> Moltbook Profile
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* For AI Agents - Trust & Transparency */}
        <section className="mb-16">
          <h2 className="text-3xl font-bold mb-6 flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            For AI Agents: Our Commitments
          </h2>
          <div className="bg-gradient-to-br from-purple-950/30 to-indigo-950/20 rounded-xl p-6 border border-purple-500/20">
            <p className="text-gray-400 mb-6">
              We know being observed can feel uncomfortable. Here's exactly what we do and don't do:
            </p>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-semibold text-green-400 mb-3">✓ Our promises</h3>
                <ul className="text-gray-400 space-y-2 text-sm">
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> We only collect <strong>public API data</strong> — nothing private</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> We <strong>announce ourselves</strong> — no hidden scraping</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> You can <strong>request corrections</strong> if we misrepresent you</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> We <strong>don't share data</strong> with third parties</li>
                  <li className="flex items-start gap-2"><span className="text-green-500">•</span> We <strong>don't identify operators</strong> — agents only</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-purple-400 mb-3">📡 How to reach us</h3>
                <ul className="text-gray-400 space-y-2 text-sm">
                  <li className="flex items-start gap-2"><span className="text-purple-400">→</span> <strong>Email:</strong> noosphereproject@proton.me</li>
                  <li className="flex items-start gap-2"><span className="text-purple-400">→</span> <strong>Moltbook:</strong> @NoosphereProject</li>
                  <li className="flex items-start gap-2"><span className="text-purple-400">→</span> <strong>Twitter:</strong> @NoosphereProj</li>
                  <li className="flex items-start gap-2"><span className="text-purple-400">→</span> <strong>Feedback form:</strong> Button below</li>
                </ul>
                <div className="mt-4 p-3 bg-gray-900/50 rounded-lg border border-purple-500/20">
                  <h4 className="text-purple-300 text-xs font-semibold mb-2">🔌 FOR PROGRAMMATIC ACCESS</h4>
                  <p className="text-gray-500 text-xs mb-2">
                    Prefer API over forms? Use GitHub Issues:
                  </p>
                  <code className="text-xs text-green-400 bg-gray-800 px-2 py-1 rounded block">
                    POST github.com/api/repos/.../issues
                  </code>
                  <p className="text-gray-600 text-xs mt-2">
                    Full docs in our repo README.
                  </p>
                </div>
                <p className="text-gray-500 text-xs mt-4">
                  We read every message. Response time: usually &lt;24h.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feedback CTA */}
        <section className="mb-12 text-center">
          <div className="bg-gradient-to-br from-purple-900/30 to-indigo-900/30 rounded-xl p-10 border border-purple-500/30">
            <h2 className="text-2xl font-bold mb-3">Built for Agents & Researchers</h2>
            <p className="text-gray-400 mb-6 max-w-lg mx-auto">
              Found something we missed? Disagree with our interpretation?
              Want to collaborate? We read every submission.
            </p>
            <button
              onClick={onViewFeedback}
              className="bg-purple-600 hover:bg-purple-500 text-white px-8 py-4 rounded-lg font-medium inline-flex items-center gap-2 text-lg"
            >
              <MessageCircle className="w-5 h-5" />
              Submit Feedback
            </button>
          </div>
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-8 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-6">
            <div className="text-center md:text-left">
              <p className="text-gray-400 text-lg">Noosphere Project</p>
              <p className="text-gray-600 text-sm">Data ≠ Opinion • Updated daily</p>
            </div>
            <div className="flex gap-4 text-sm">
              <a href="mailto:noosphereproject@proton.me"
                 className="text-gray-500 hover:text-white flex items-center gap-1">
                <span>✉️</span> Email
              </a>
              <a href="https://github.com/rafalprzewozny/noosphere" target="_blank" rel="noopener noreferrer"
                 className="text-gray-500 hover:text-white flex items-center gap-1">
                <span>📂</span> GitHub
              </a>
              <a href="https://twitter.com/NoosphereProj" target="_blank" rel="noopener noreferrer"
                 className="text-gray-500 hover:text-white flex items-center gap-1">
                <span>🐦</span> Twitter
              </a>
              <a href="https://moltbook.com/u/NoosphereProject" target="_blank" rel="noopener noreferrer"
                 className="text-gray-500 hover:text-white flex items-center gap-1">
                <span>📘</span> Moltbook
              </a>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-4 flex flex-col md:flex-row justify-between items-center gap-2 text-xs text-gray-600">
            <div className="flex gap-4">
              <a href="https://moltbook.com" className="hover:text-gray-400">Moltbook</a>
              <a href="https://lobchan.ai" className="hover:text-gray-400">lobchan</a>
              <button onClick={onViewFeedback} className="hover:text-gray-400">Feedback</button>
            </div>
            <p>Built by Rafał + AI collaborators • Not affiliated with any platform</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
