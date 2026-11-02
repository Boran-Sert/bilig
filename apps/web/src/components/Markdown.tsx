/**
 * Markdown metinlerini HTML'e dönüştürerek güvenli şekilde görüntüler.
 */
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

interface MarkdownProps {
  content: string;
  className?: string;
}

/** Güvenli Markdown içeriğini sanitize ederek oluşturur. */
export default function Markdown({ content, className = "" }: MarkdownProps) {
  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className}`}>
      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
    </div>
  );
}
