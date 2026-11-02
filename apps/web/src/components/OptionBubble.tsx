/**
 * Test sorusu seçeneklerindeki harf balonunu (A, B, C, D, E) görüntüler.
 */

export type OptionStatus = "default" | "selected" | "correct" | "wrong";

interface OptionBubbleProps {
  label: string;
  status?: OptionStatus;
}

/** Şık harfi balonunu durumuna göre renklendirerek oluşturur. */
export default function OptionBubble({ label, status = "default" }: OptionBubbleProps) {
  let colorClasses = "border-border bg-background text-foreground";

  if (status === "selected") {
    colorClasses = "border-primary bg-primary text-primary-foreground";
  } else if (status === "correct") {
    colorClasses = "border-emerald-600 bg-emerald-600 text-white dark:bg-emerald-500";
  } else if (status === "wrong") {
    colorClasses = "border-destructive bg-destructive text-destructive-foreground";
  }

  return (
    <span
      className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors ${colorClasses}`}
    >
      {label}
    </span>
  );
}
