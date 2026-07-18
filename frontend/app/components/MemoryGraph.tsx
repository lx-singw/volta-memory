"use client";

import dynamic from "next/dynamic";
import { useMemo, useState, useEffect } from "react";

// Dynamically import react-force-graph-2d to avoid SSR 'window is not defined' errors
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <div style={{ color: "#94a3b8", textAlign: "center", padding: "2rem" }}>Initializing Neural Graph...</div>
});

type MemoryGraphProps = {
  memories: any[];
};

export default function MemoryGraph({ memories }: MemoryGraphProps) {
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Handle window resizing for the canvas
  useEffect(() => {
    function handleResize() {
      // Find the container width
      const container = document.getElementById("graph-container");
      if (container) {
        setDimensions({
          width: container.clientWidth,
          height: window.innerHeight - 200,
        });
      }
    }
    window.addEventListener("resize", handleResize);
    handleResize(); // Initial measurement
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const graphData = useMemo(() => {
    const nodes: any[] = [];
    const links: any[] = [];

    // Central Node (The AI's Core)
    nodes.push({
      id: "core",
      name: "Volta Core",
      group: "core",
      val: 20,
      color: "#facc15" // Bright yellow/gold for the solar theme core
    });

    const topicsMap = new Map<string, string>(); // topic -> first node ID of that topic

    memories.forEach((mem) => {
      // Determine color and size based on confidence and type
      let color = "#3b82f6"; // default blue
      if (mem.memory_type === "preference") color = "#a855f7"; // purple
      if (mem.memory_type === "outcome") color = "#10b981"; // green
      
      // Decay visualization: lower confidence = smaller, dimmer node
      const conf = mem.confidence || 0.5;
      const size = Math.max(3, conf * 10);
      
      // Node
      nodes.push({
        id: mem.memory_id,
        name: mem.content,
        topic: mem.topic,
        type: mem.memory_type,
        val: size,
        color: color,
        confidence: conf,
      });

      // Link to Core
      links.push({
        source: "core",
        target: mem.memory_id,
        value: 1,
        color: "rgba(59, 130, 246, 0.2)"
      });

      // Semantic Linking: Link memories sharing the same topic
      if (mem.topic) {
        if (topicsMap.has(mem.topic)) {
          links.push({
            source: topicsMap.get(mem.topic),
            target: mem.memory_id,
            value: 2,
            color: "rgba(255, 255, 255, 0.15)"
          });
        } else {
          topicsMap.set(mem.topic, mem.memory_id);
        }
      }
    });

    return { nodes, links };
  }, [memories]);

  if (memories.length === 0) {
    return <div style={{ color: "#94a3b8", textAlign: "center", padding: "2rem", border: "1px dashed #334155", borderRadius: 8 }}>No memories stored yet. The neural graph is empty.</div>;
  }

  return (
    <div id="graph-container" style={{ 
      width: "100%", 
      borderRadius: "12px", 
      overflow: "hidden", 
      background: "#020617", // Very dark background
      border: "1px solid #1e293b",
      boxShadow: "0 4px 25px rgba(0,0,0,0.5)"
    }}>
      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        graphData={graphData}
        nodeLabel={(node: any) => {
          if (node.id === "core") return node.name;
          return `[${node.topic || 'General'}] ${node.name}\nConfidence: ${Math.round(node.confidence * 100)}%`;
        }}
        nodeColor={(node: any) => node.color}
        nodeRelSize={6}
        linkColor={(link: any) => link.color}
        linkWidth={(link: any) => link.value}
        backgroundColor="#020617"
        onNodeHover={(node: any) => {
          // Could add custom hover state logic here
          document.body.style.cursor = node ? 'pointer' : 'default';
        }}
      />
    </div>
  );
}
