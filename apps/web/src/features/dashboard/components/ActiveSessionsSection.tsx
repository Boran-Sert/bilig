/**
 * Öğrencinin yarım bıraktığı aktif test oturumlarını listeler ve devam bağlantısı sunar.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { buttonVariants } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";
import type { DashboardActiveSession } from "../types";

interface ActiveSessionsSectionProps {
  sessions: DashboardActiveSession[];
}

/**
 * Devam eden testleri ve ilerleme durumunu gösterir.
 */
export default function ActiveSessionsSection({ sessions }: ActiveSessionsSectionProps) {
  const { t } = useTranslation("dashboard");

  return (
    <section className="space-y-3 rounded-xl border border-border bg-card p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">{t("activeSessions.title")}</h2>

      {sessions.length === 0 ? (
        <p className="py-4 text-xs text-muted-foreground">{t("activeSessions.empty")}</p>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.sessionId}
              className="flex flex-col gap-2 rounded-lg border border-border/60 bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{session.examTitle}</p>
                <p className="text-xs text-muted-foreground">
                  {t("activeSessions.progress", {
                    current: session.answeredCount,
                    total: session.questionCount,
                  })}
                </p>
              </div>
              <Link
                to={`/tests/${session.examId}/solve`}
                className={cn(buttonVariants({ size: "sm" }), "w-full sm:w-auto")}
              >
                {t("activeSessions.resume")}
              </Link>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
