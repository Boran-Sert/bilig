/**
 * Yanlış cevabın akışla gelen anlatımını ve kaynak alıntı kartlarını gösterir.
 */
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import Markdown from "../../../components/Markdown";
import { useExplanationStream } from "../useExplanationStream";
import CitationCard from "./CitationCard";

interface ExplanationSectionProps {
  sessionId: number;
  questionId: number;
}

/**
 * Anlatım akışını başlatır, canlı metni ve alıntı kartlarını çizer.
 */
export default function ExplanationSection({ sessionId, questionId }: ExplanationSectionProps) {
  const { t } = useTranslation("test");
  const { text, citationBlockIds, isStreaming, isDone, error, startExplanation } =
    useExplanationStream();

  useEffect(() => {
    startExplanation(sessionId, questionId);
  }, [sessionId, questionId, startExplanation]);

  return (
    <aside
      aria-label={t("solve.whyWrong")}
      className="space-y-4 rounded-xl border border-border bg-card p-5 shadow-xs"
    >
      <div className="flex items-center justify-between border-b border-border pb-3">
        <h2 className="text-base font-semibold tracking-tight">{t("solve.whyWrong")}</h2>
        <span className="text-xs font-medium text-muted-foreground">{t("solve.styleLabel")}</span>
      </div>

      <div className="space-y-4 text-sm leading-relaxed text-foreground">
        {text ? (
          <div className="rounded-lg bg-muted/40 p-4 leading-relaxed">
            <Markdown content={text} />
          </div>
        ) : isStreaming ? (
          <p className="text-xs text-muted-foreground animate-pulse">
            {t("solve.explanationLoading")}
          </p>
        ) : null}

        {error && (
          <p role="alert" className="rounded-md bg-destructive/10 p-3 text-xs text-destructive">
            {error}
          </p>
        )}

        {citationBlockIds.length > 0 && (
          <div className="space-y-3 pt-2">
            {citationBlockIds.map((blockId) => (
              <CitationCard key={blockId} blockId={blockId} />
            ))}
          </div>
        )}

        {isStreaming && !isDone && text && (
          <span className="inline-block h-2 w-2 rounded-full bg-primary animate-ping" />
        )}
      </div>
    </aside>
  );
}
