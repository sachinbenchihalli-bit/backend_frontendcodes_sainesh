"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

const mathConfig = {
  singleDollarTextMath: false,
};

interface ProgressiveMarkdownProps {
  content: string;
  // These props are kept for API compatibility but are no longer used.
  // The backend already streams tokens one-by-one, so no artificial
  // word-by-word animation is needed (and it was causing the freeze).
  initialDelay?: number;
  wordsPerTick?: number;
  tickInterval?: number;
}

/**
 
 * THE FIX:
 *   Render `content` directly. The parent (CampaignOptimizationChat) already
 *   grows message.text token-by-token via onChunk. No local animation needed
 *   — the backend streaming IS the progressive display.
 */
export function ProgressiveMarkdown({ content }: ProgressiveMarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[[remarkMath, mathConfig], remarkGfm]}
      rehypePlugins={[rehypeKatex]}
      components={{
        h1: ({ node, ...props }) => <h1 className="text-2xl font-extrabold pl-1.5 mt-1 mb-1" {...props} />,
        h2: ({ node, ...props }) => <h2 className="text-xl font-bold pl-1.5 mt-1 mb-1" {...props} />,
        h3: ({ node, ...props }) => <h3 className="text-lg font-semibold pl-1.5 mt-5 mb-1" {...props} />,
        h4: ({ node, ...props }) => <h3 className="text-base font-semibold pl-1.5 mt-1 mb-1" {...props} />,
        p: ({ node, ...props }) => <p className="font-normal mb-2 pl-2" {...props} />,
        strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
        em: ({ node, ...props }) => <em className="italic" {...props} />,
        ul: ({ node, ...props }) => <ul className="list-disc pl-5 ml-2 mt-1 mb-3 space-y-1 leading-tight" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal pl-5 ml-2 my-1 space-y-1 leading-tight" {...props} />,
        li: ({ node, ...props }) => <li className="m-0" {...props} />,
        a: ({ href, children, ...props }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline" {...props}>
            {children}
          </a>
        ),
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" {...props} />
          </div>
        ),
        th: ({ node, ...props }) => <th className="border px-2 py-1 bg-gray-50" {...props} />,
        td: ({ node, ...props }) => <td className="border px-2 py-1" {...props} />,
        br: () => <br />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
