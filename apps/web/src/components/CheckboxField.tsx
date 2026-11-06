/**
 * Etiketi, açıklaması ve hata mesajıyla tek onay kutusu.
 */
import type { ComponentProps } from "react";

interface CheckboxFieldProps extends Omit<ComponentProps<"input">, "type"> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

/**
 * Etiketli onay kutusunu ve varsa açıklama ile hata mesajını gösterir.
 * @param props Kutunun etiketi, açıklaması, hatası ve girdi özellikleri.
 * @returns Onay kutusu alanı.
 */
export default function CheckboxField({
  id,
  label,
  hint,
  error,
  ...inputProps
}: CheckboxFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="flex items-start gap-2 text-sm">
        <input
          id={id}
          type="checkbox"
          className="mt-0.5 size-4 accent-navy"
          aria-invalid={Boolean(error)}
          aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
          {...inputProps}
        />
        {label}
      </label>
      {hint && (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
