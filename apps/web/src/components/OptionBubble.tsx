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
  let colorClasses = "border-input bg-card text-heading";

  if (status === "selected") {
    colorClasses = "border-navy bg-navy text-white";
  } else if (status === "correct") {
    colorClasses = "border-success bg-success text-white";
  } else if (status === "wrong") {
    colorClasses = "border-destructive bg-destructive text-white";
  }

  return (
    <span
      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors ${colorClasses}`}
    >
      {label}
    </span>
  );
}
