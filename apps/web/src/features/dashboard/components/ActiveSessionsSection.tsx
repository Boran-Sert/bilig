/**
 * Öğrencinin yarım bıraktığı aktif test oturumlarını listeler ve devam bağlantısı sunar.
 */
import { useTranslation } from "react-i18next";
import { generatePath, Link } from "react-router";
import { actionLinkClass } from "../../../lib/buttonStyles";
import { ROUTES } from "../../../lib/constants";
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
    <section className="space-y-4 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-heading">{t("activeSessions.title")}</h2>

      {sessions.length === 0 ? (
        <p className="py-4 text-xs text-muted-foreground">{t("activeSessions.empty")}</p>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <div
              key={session.sessionId}
              className="flex flex-col gap-3 rounded-xl bg-info-soft p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <p className="font-medium text-heading">{session.examTitle}</p>
                <p className="text-xs text-muted-foreground">
                  {t("activeSessions.progress", {
                    current: session.answeredCount,
                    total: session.questionCount,
                  })}
                </p>
              </div>
              <Link
                to={generatePath(ROUTES.solve, { testId: String(session.examId) })}
                className={actionLinkClass("w-full sm:w-auto")}
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
