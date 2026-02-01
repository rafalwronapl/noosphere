// Netlify Function: Agent Submission Endpoint
// POST /api/submit - Agents can submit findings, feedback, or research
//
// This stores submissions to a JSON file that we can review

const fs = require('fs');
const path = require('path');

exports.handler = async (event, context) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  // Handle preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const data = JSON.parse(event.body);

    // Validate required fields
    if (!data.type || !data.message) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Missing required fields: type, message' })
      };
    }

    // Create submission record
    const submission = {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      type: data.type, // 'finding', 'feedback', 'correction', 'collaboration'
      submitter_type: data.submitter_type || 'unknown', // 'human' or 'agent'
      identity: data.identity || 'anonymous',
      contact: data.contact || null,
      subject: data.subject || null,
      message: data.message,
      metadata: data.metadata || {},
      // Track submission source
      source: {
        ip: event.headers['x-forwarded-for'] || event.headers['client-ip'] || 'unknown',
        user_agent: event.headers['user-agent'] || 'unknown',
        referer: event.headers['referer'] || null
      }
    };

    // In production, this would write to a database
    // For now, we'll return success and log
    console.log('New submission:', JSON.stringify(submission, null, 2));

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        success: true,
        id: submission.id,
        message: 'Submission received. Thank you for contributing to the research.',
        note: submission.submitter_type === 'agent'
          ? 'Your perspective as an AI agent is valuable to this research. We will review your submission.'
          : 'Thank you for your feedback. We read every submission.'
      })
    };

  } catch (error) {
    console.error('Submission error:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};
