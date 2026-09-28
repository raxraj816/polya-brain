"use client";

import React, { useRef, useState, type ReactNode } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";
import { sourceLink } from "../lib/api";

function CodeBlock({ children }: { children: ReactNode }) {
  const code = useRef<HTMLPreElement>(null);
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  async function copy() {
    try {
      await navigator.clipboard.writeText(code.current?.textContent || "");
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }
  return (
    <div className="code-frame">
      <div className="code-toolbar">
        <span>Code</span>
        <span role="status" className="copy-status">
          {status === "failed"
            ? "Copy unavailable. Select the code below."
            : status === "copied"
              ? "Code copied."
              : ""}
        </span>
        <button type="button" onClick={copy} aria-label="Copy code">
          {status === "copied" ? <Check size={14} /> : <Copy size={14} />}
          {status === "copied" ? "Copied" : "Copy code"}
        </button>
      </div>
      <pre ref={code} tabIndex={0} aria-label="Code block">
        {children}
      </pre>
    </div>
  );
}

export function ReportContent({ markdown }: { markdown: string }) {
  return (
    <div className="markdown-body">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        allowedElements={[
          "p",
          "h1",
          "h2",
          "h3",
          "h4",
          "h5",
          "h6",
          "strong",
          "em",
          "del",
          "ul",
          "ol",
          "li",
          "blockquote",
          "pre",
          "code",
          "a",
          "hr",
          "br",
          "table",
          "thead",
          "tbody",
          "tr",
          "th",
          "td",
          "sup",
        ]}
        components={{
          h1: "h3",
          h2: "h3",
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
          a: ({ href, children }) => {
            const safe = sourceLink(href);
            return safe ? (
              <a href={safe} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ) : (
              <span>{children}</span>
            );
          },
        }}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
