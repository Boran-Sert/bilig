/**
 * Soru ve kaynak metinlerindeki Markdown'ı yalnız izin verilen etiketlerle güvenli şekilde gösterir.
 */
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema, type Options as SanitizeOptions } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { MARKDOWN_ALLOWED_TAGS } from "../lib/constants";

interface MarkdownProps {
  content: string;
  className?: string;
}

const SANITIZE_SCHEMA: SanitizeOptions = {
  ...defaultSchema,
  tagNames: MARKDOWN_ALLOWED_TAGS,
  attributes: { th: ["align"], td: ["align"] },
};

const CONTENT_CLASSES =
  "space-y-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_table]:border-collapse [&_td]:border " +
  "[&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-border " +
  "[&_th]:px-2 [&_th]:py-1 [&_ul]:list-disc [&_ul]:pl-5";

/** Markdown'ı GFM ile çevirir, HTML'de yalnız altı çizili etiketine izin verir. */
export default function Markdown({ content, className = "" }: MarkdownProps) {
  return (
    <div className={`${CONTENT_CLASSES} ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, SANITIZE_SCHEMA]]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
