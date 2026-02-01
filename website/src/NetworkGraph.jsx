import { useEffect, useRef, useState } from 'react';

/**
 * Simple force-directed network graph visualization
 * Shows agent interactions as nodes and edges
 */
export default function NetworkGraph({ data }) {
  const canvasRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [simulation, setSimulation] = useState(null);

  useEffect(() => {
    if (!data || !data.nodes || !data.edges) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Initialize node positions
    const nodes = data.nodes.map((n, i) => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
      radius: Math.min(5 + Math.sqrt(n.size || 1) * 0.5, 20)
    }));

    // Build edge lookup
    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = n);

    const edges = data.edges
      .filter(e => nodeMap[e.source] && nodeMap[e.target])
      .map(e => ({
        source: nodeMap[e.source],
        target: nodeMap[e.target],
        weight: e.weight || 1
      }));

    // Simple force simulation
    let animationId;
    let iterations = 0;
    const maxIterations = 300;

    function simulate() {
      iterations++;

      // Apply forces
      nodes.forEach(node => {
        // Center gravity
        node.vx += (width / 2 - node.x) * 0.001;
        node.vy += (height / 2 - node.y) * 0.001;

        // Repulsion between nodes
        nodes.forEach(other => {
          if (node === other) return;
          const dx = node.x - other.x;
          const dy = node.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 500 / (dist * dist);
          node.vx += dx * force * 0.01;
          node.vy += dy * force * 0.01;
        });
      });

      // Edge attraction
      edges.forEach(edge => {
        const dx = edge.target.x - edge.source.x;
        const dy = edge.target.y - edge.source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 100) * 0.001;
        edge.source.vx += dx * force;
        edge.source.vy += dy * force;
        edge.target.vx -= dx * force;
        edge.target.vy -= dy * force;
      });

      // Apply velocity with damping
      nodes.forEach(node => {
        node.vx *= 0.9;
        node.vy *= 0.9;
        node.x += node.vx;
        node.y += node.vy;
        // Keep in bounds
        node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
      });

      // Draw
      ctx.fillStyle = '#111827';
      ctx.fillRect(0, 0, width, height);

      // Draw edges
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.3)';
      ctx.lineWidth = 0.5;
      edges.forEach(edge => {
        ctx.beginPath();
        ctx.moveTo(edge.source.x, edge.source.y);
        ctx.lineTo(edge.target.x, edge.target.y);
        ctx.stroke();
      });

      // Draw nodes
      nodes.forEach(node => {
        const isSelected = selectedNode === node.id;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);

        // Color by in/out balance
        const inRatio = node.in_degree / (node.in_degree + node.out_degree + 1);
        if (inRatio > 0.6) {
          ctx.fillStyle = isSelected ? '#22d3ee' : '#06b6d4'; // Cyan - influencer
        } else if (inRatio < 0.4) {
          ctx.fillStyle = isSelected ? '#a78bfa' : '#8b5cf6'; // Purple - broadcaster
        } else {
          ctx.fillStyle = isSelected ? '#4ade80' : '#22c55e'; // Green - balanced
        }
        ctx.fill();

        // Label for larger nodes
        if (node.radius > 8 || isSelected) {
          ctx.fillStyle = '#fff';
          ctx.font = '10px monospace';
          ctx.textAlign = 'center';
          ctx.fillText(node.id, node.x, node.y - node.radius - 4);
        }
      });

      if (iterations < maxIterations) {
        animationId = requestAnimationFrame(simulate);
      }
    }

    simulate();

    // Click handler
    const handleClick = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      for (const node of nodes) {
        const dx = x - node.x;
        const dy = y - node.y;
        if (dx * dx + dy * dy < node.radius * node.radius) {
          setSelectedNode(node.id);
          return;
        }
      }
      setSelectedNode(null);
    };

    canvas.addEventListener('click', handleClick);

    return () => {
      cancelAnimationFrame(animationId);
      canvas.removeEventListener('click', handleClick);
    };
  }, [data, selectedNode]);

  const selectedData = data?.nodes?.find(n => n.id === selectedNode);

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-white">Interaction Network</h3>
        <div className="flex gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-cyan-500"></span>
            <span className="text-gray-400">Influencer</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-purple-500"></span>
            <span className="text-gray-400">Broadcaster</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-gray-400">Balanced</span>
          </span>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        width={600}
        height={400}
        className="w-full rounded border border-gray-700 cursor-pointer"
      />

      {selectedData && (
        <div className="mt-3 p-3 bg-gray-800 rounded text-sm">
          <div className="font-bold text-white">{selectedData.id}</div>
          <div className="text-gray-400 mt-1">
            In: {selectedData.in_degree} | Out: {selectedData.out_degree} | Posts: {selectedData.posts}
          </div>
        </div>
      )}

      <div className="mt-2 text-xs text-gray-500">
        {data?.nodes?.length || 0} nodes, {data?.edges?.length || 0} edges
      </div>
    </div>
  );
}
