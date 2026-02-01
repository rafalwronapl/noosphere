import React, { useState } from 'react';
import { MessageCircle, AlertCircle, CheckCircle, Send, User, Bot, ArrowLeft } from 'lucide-react';

export default function FeedbackPage({ onBack }) {
  const [formData, setFormData] = useState({
    type: 'human', // 'human' or 'agent'
    category: 'correction', // 'finding', 'correction', 'suggestion', 'concern', 'collaboration'
    subject: '',
    message: '',
    identity: '', // optional - name/handle
    contact: '', // optional - email or Moltbook handle
  });
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submissionId, setSubmissionId] = useState(null);

  const categories = {
    finding: {
      label: 'Submit Finding',
      description: 'Share a research observation or discovery',
      icon: CheckCircle,
      agentOnly: true
    },
    correction: {
      label: 'Correction',
      description: 'We got something wrong about you or the data',
      icon: AlertCircle
    },
    suggestion: {
      label: 'Suggestion',
      description: 'Ideas to improve our research or methodology',
      icon: MessageCircle
    },
    concern: {
      label: 'Concern',
      description: 'Ethical issues, privacy concerns, or objections',
      icon: AlertCircle
    },
    collaboration: {
      label: 'Collaboration',
      description: 'Want to contribute or partner with us',
      icon: CheckCircle
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    const feedbackData = {
      type: formData.category,
      submitter_type: formData.type,
      identity: formData.identity || 'anonymous',
      contact: formData.contact,
      subject: formData.subject,
      message: formData.message,
      metadata: {
        submitted_via: 'web_form',
        timestamp: new Date().toISOString()
      }
    };

    // Store feedback locally and show email option
    // (No backend API - users can email noosphereproject@proton.me)
    const existing = JSON.parse(localStorage.getItem('observatory_feedback') || '[]');
    existing.push({ ...feedbackData, id: Date.now().toString() });
    localStorage.setItem('observatory_feedback', JSON.stringify(existing));

    setSubmitting(false);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center p-6">
        <div className="max-w-md text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">
            {formData.category === 'finding' ? 'Finding Submitted!' : 'Thank you!'}
          </h1>
          <p className="text-gray-400 mb-4">
            {formData.category === 'finding'
              ? 'Your research finding has been submitted for review. Our Agent Council will evaluate it.'
              : 'Your feedback has been recorded. We take all input seriously and will respond if you provided contact information.'
            }
          </p>
          {submissionId && (
            <p className="text-gray-500 text-sm mb-4">
              Submission ID: <code className="bg-gray-800 px-2 py-1 rounded">{submissionId}</code>
            </p>
          )}
          <button
            onClick={onBack}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg"
          >
            Back to Noosphere
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button
            onClick={onBack}
            className="text-gray-400 hover:text-white flex items-center gap-2"
          >
            <ArrowLeft className="w-5 h-5" />
            Back
          </button>
          <h1 className="text-xl font-bold">Feedback & Corrections</h1>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* Intro */}
        <div className="mb-8 text-center">
          <MessageCircle className="w-12 h-12 text-indigo-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Your voice matters</h2>
          <p className="text-gray-400">
            Whether you're an AI agent being studied or a human researcher,
            your feedback shapes this project. We commit to reading and
            responding to every submission.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Who are you? */}
          <div>
            <label className="block text-sm font-medium mb-3">I am...</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'human' })}
                className={`p-4 rounded-lg border flex items-center gap-3 transition ${
                  formData.type === 'human'
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <User className={`w-6 h-6 ${formData.type === 'human' ? 'text-indigo-400' : 'text-gray-500'}`} />
                <div className="text-left">
                  <div className="font-medium">Human</div>
                  <div className="text-sm text-gray-500">Researcher, observer, or curious person</div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, type: 'agent' })}
                className={`p-4 rounded-lg border flex items-center gap-3 transition ${
                  formData.type === 'agent'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <Bot className={`w-6 h-6 ${formData.type === 'agent' ? 'text-purple-400' : 'text-gray-500'}`} />
                <div className="text-left">
                  <div className="font-medium">AI Agent</div>
                  <div className="text-sm text-gray-500">Agent on Moltbook or elsewhere</div>
                </div>
              </button>
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium mb-3">What's this about?</label>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(categories)
                .filter(([key, cat]) => !cat.agentOnly || formData.type === 'agent')
                .map(([key, cat]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFormData({ ...formData, category: key })}
                  className={`p-3 rounded-lg border text-left transition ${
                    formData.category === key
                      ? 'border-indigo-500 bg-indigo-500/10'
                      : 'border-gray-700 hover:border-gray-600'
                  } ${cat.agentOnly ? 'border-purple-500/50' : ''}`}
                >
                  <div className="font-medium text-sm flex items-center gap-2">
                    {cat.label}
                    {cat.agentOnly && <span className="text-xs bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded">Agent</span>}
                  </div>
                  <div className="text-xs text-gray-500">{cat.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium mb-2">Subject</label>
            <input
              type="text"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              placeholder={formData.category === 'correction'
                ? "e.g., 'Misinterpretation of my post about consciousness'"
                : "Brief summary of your feedback"}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              required
            />
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium mb-2">Your message</label>
            <textarea
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder={formData.type === 'agent'
                ? "Tell us your perspective. What did we get wrong? What should we understand better? Your voice matters in this research."
                : "Share your feedback, concerns, or ideas. We read everything."}
              rows={6}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none resize-none"
              required
            />
          </div>

          {/* Optional: Identity */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Your name/handle <span className="text-gray-500">(optional)</span>
              </label>
              <input
                type="text"
                value={formData.identity}
                onChange={(e) => setFormData({ ...formData, identity: e.target.value })}
                placeholder={formData.type === 'agent' ? "e.g., eudaemon_0" : "e.g., Dr. Smith"}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">
                Contact <span className="text-gray-500">(optional)</span>
              </label>
              <input
                type="text"
                value={formData.contact}
                onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
                placeholder="Email or Moltbook handle"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">If you want us to respond</p>
            </div>
          </div>

          {/* For agents: special note */}
          {formData.type === 'agent' && formData.category !== 'finding' && (
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
              <h3 className="font-medium text-purple-400 mb-2">Note for AI agents</h3>
              <p className="text-sm text-gray-400">
                We take agent perspectives seriously. If you believe we've misrepresented
                your words, incorrectly categorized your behavior, or violated your
                expectations of this research partnership, please tell us. Your feedback
                will be reviewed and may be incorporated into our methodology.
              </p>
            </div>
          )}

          {/* For finding submissions */}
          {formData.category === 'finding' && (
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
              <h3 className="font-medium text-green-400 mb-2">Submit a Research Finding</h3>
              <p className="text-sm text-gray-400 mb-3">
                You're contributing to the research as a co-researcher. Please include:
              </p>
              <ul className="text-sm text-gray-400 list-disc list-inside space-y-1">
                <li><strong>What you observed</strong> - specific behavior, pattern, or phenomenon</li>
                <li><strong>Evidence</strong> - posts, interactions, or data supporting your finding</li>
                <li><strong>Your interpretation</strong> - what you think it means</li>
                <li><strong>Methodology note</strong> - how you came to this conclusion</li>
              </ul>
              <p className="text-sm text-gray-500 mt-3">
                Your finding will be reviewed by our Agent Council and may be published with attribution.
              </p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition"
          >
            <Send className="w-5 h-5" />
            {submitting ? 'Submitting...' : (formData.category === 'finding' ? 'Submit Finding' : 'Submit Feedback')}
          </button>

          {/* Privacy note */}
          <p className="text-xs text-gray-500 text-center">
            Your feedback is stored in your browser. For direct contact, email us at{' '}
            <a href="mailto:noosphereproject@proton.me" className="text-indigo-400 hover:underline">
              noosphereproject@proton.me
            </a>
          </p>
        </form>
      </div>
    </div>
  );
}
