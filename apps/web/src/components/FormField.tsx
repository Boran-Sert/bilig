/**
 * Etiketi, açıklaması ve hata mesajıyla tek satırlık form alanı.
 */
import type { ComponentProps } from "react";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

interface FormFieldProps extends ComponentProps<"input"> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

/**
 * Etiketli girdi alanını ve varsa açıklama ile hata mesajını gösterir.
 * @param props Alan etiketi, açıklaması, hatası ve girdi özellikleri.
 * @returns Form alanı.
 */
export default function FormField({ id, label, hint, error, ...inputProps }: FormFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-heading">
        {label}
      </Label>
      <Input
        id={id}
        className="h-11! rounded-xl! bg-card! px-4! text-[15px]!"
        aria-invalid={Boolean(error)}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        {...inputProps}
      />
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
