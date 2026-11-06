/**
 * Soru yanındaki sohbet panelinin lacivert başlıklı ve uzun gövdeli çerçevesini sunar.
 */
import type { ReactNode } from "react";

interface ChatPanelShellProps {
  title: string;
  note?: string;
  ariaLabel: string;
  children: ReactNode;
  footer: ReactNode;
}

/**
 * Başlığı, kaydırılabilir mesaj alanını ve alt girdi alanını sabit yükseklikte düzenler.
 * @param props Başlık, not, erişilebilir ad, mesajlar ve alt alan.
 * @returns Sohbet paneli çerçevesi.
 */
export default function ChatPanelShell({
  title,
  note,
  ariaLabel,
  children,
  footer,
}: ChatPanelShellProps) {
  return (
    <aside
      aria-label={ariaLabel}
      className="flex min-h-[520px] flex-col overflow-hidden rounded-2xl border border-navy/15 bg-card shadow-md lg:h-[calc(100vh-9rem)] lg:min-h-[640px]"
    >
      <div className="flex items-center justify-between gap-3 bg-navy px-5 py-4 text-white">
        <h2 className="text-base font-semibold tracking-tight text-white">{title}</h2>
        {note && <span className="text-xs font-medium text-white/70">{note}</span>}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto bg-info-soft/60 p-5">{children}</div>

      <div className="border-t border-border bg-card p-4">{footer}</div>
    </aside>
  );
}
