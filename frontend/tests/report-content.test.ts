import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { ReportContent } from "../components/report-content";

const render = (markdown: string) =>
  renderToStaticMarkup(createElement(ReportContent, { markdown }));

describe("readable, non-executing reports", () => {
  it("renders report structure, code indentation, and a copy action", () => {
    const html = render(
      "### Implementation\n\n```python\ndef f(x):\n    return x < 3\n```\n\n**Checks**\n\n- Empty input\n- Boundaries",
    );
    expect(html).toContain("<h3>Implementation</h3>");
    expect(html).toContain("<strong>Checks</strong>");
    expect(html).toContain("<li>Empty input</li>");
    expect(html).toContain('aria-label="Copy code"');
    expect(html).toContain("def f(x):\n    return x &lt; 3\n");
  });
  it("blocks raw HTML, unsafe links, and remotely loaded images", () => {
    const html = render(
      '<script>alert(1)</script>\n\n<img src="https://example.com/beacon" onerror="alert(1)">\n\n![remote](https://example.com/beacon)\n\n[bad](javascript:alert%281%29)\n\n[file](file:///private/source.py)\n\n[good](https://example.com/source)',
    );
    expect(html).not.toMatch(
      /<script|<img|javascript:|file:\/\/\/|beacon|onerror=/,
    );
    expect(html).toContain('href="https://example.com/source"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("bad");
    expect(html).toContain("file");
  });
  it("renders tables without enabling embedded controls", () => {
    const html = render(
      "| Check | Result |\n| --- | --- |\n| Boundaries | Passed |\n\n<input value='run code'>",
    );
    expect(html).toContain("<table>");
    expect(html).toContain("<td>Passed</td>");
    expect(html).not.toContain("<input");
  });
});
