import { useState, type ReactNode } from "react";

type Block =
  | { kind: "code"; lang: string; text: string }
  | { kind: "heading"; level: number; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "quote"; text: string }
  | { kind: "paragraph"; text: string };

export function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const fence = /^```\s*([\w+-]*)/.exec(line);
    if (fence) {
      const body: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        body.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push({ kind: "code", lang: fence[1], text: body.join("\n") });
      continue;
    }
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push({
        kind: "heading",
        level: heading[1].length,
        text: heading[2],
      });
      index += 1;
      continue;
    }
    const item = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(line);
    if (item) {
      const ordered = /\d/.test(item[1]);
      const items: string[] = [];
      while (index < lines.length) {
        const next = /^\s*([-*+]|\d+[.)])\s+(.*)$/.exec(lines[index]);
        if (!next || /\d/.test(next[1]) !== ordered) break;
        items.push(next[2]);
        index += 1;
      }
      blocks.push({ kind: "list", ordered, items });
      continue;
    }
    if (line.startsWith(">")) {
      const body: string[] = [];
      while (index < lines.length && lines[index].startsWith(">")) {
        body.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ kind: "quote", text: body.join("\n") });
      continue;
    }
    if (!line.trim()) {
      index += 1;
      continue;
    }
    const body: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(```|#{1,4}\s|>|\s*([-*+]|\d+[.)])\s)/.test(lines[index])
    ) {
      body.push(lines[index]);
      index += 1;
    }
    blocks.push({ kind: "paragraph", text: body.join("\n") });
  }
  return blocks;
}

const inlinePattern =
  /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)|(\[[^\]]+\]\([^)\s]+\))/g;

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(inlinePattern)) {
    const at = match.index;
    if (at > last) parts.push(text.slice(last, at));
    const token = match[0];
    const key = `${at}-${token.length}`;
    if (match[1]) parts.push(<code key={key}>{token.slice(1, -1)}</code>);
    else if (match[2])
      parts.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    else if (match[3]) parts.push(<em key={key}>{token.slice(1, -1)}</em>);
    else {
      // Links are shown, never followed: model output is untrusted.
      const [, label, url] = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(token) ?? [];
      parts.push(
        <span key={key} className="md-link" title={url}>
          {label} <small>({url})</small>
        </span>,
      );
    }
    last = at + token.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function CodeBlock({ lang, text }: { lang: string; text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="md-code">
      <div className="md-code-bar">
        <span>{lang || "text"}</span>
        <button
          type="button"
          onClick={() =>
            void navigator.clipboard
              .writeText(text)
              .then(() => setCopied(true))
              .catch(() => setCopied(false))
          }
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code>{text}</code>
      </pre>
    </div>
  );
}

export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      {parseBlocks(text).map((block, index) => {
        switch (block.kind) {
          case "code":
            return (
              <CodeBlock key={index} lang={block.lang} text={block.text} />
            );
          case "heading": {
            const Tag = `h${Math.min(6, block.level + 2)}` as "h3";
            return <Tag key={index}>{inline(block.text)}</Tag>;
          }
          case "list": {
            const Tag = block.ordered ? "ol" : "ul";
            return (
              <Tag key={index}>
                {block.items.map((item, row) => (
                  <li key={row}>{inline(item)}</li>
                ))}
              </Tag>
            );
          }
          case "quote":
            return <blockquote key={index}>{inline(block.text)}</blockquote>;
          default:
            return <p key={index}>{inline(block.text)}</p>;
        }
      })}
    </div>
  );
}
