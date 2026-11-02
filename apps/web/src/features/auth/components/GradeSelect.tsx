/**
 * Kayıt formunda sunucunun verdiği sınıfları açılır listede gösterir.
 */
import type { ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Label } from "../../../components/ui/label";
import { getProblemMessage } from "../../../lib/api/problem";
import { useRegisterOptions } from "../api";

interface GradeSelectProps extends ComponentProps<"select"> {
  error?: string;
}

/**
 * Sınıf listesini, yüklenme hatasını ve alan hatasını gösterir.
 * @param props Alan hatası ve select özellikleri.
 * @returns Sınıf seçim alanı.
 */
export default function GradeSelect({ error, ...selectProps }: GradeSelectProps) {
  const { t } = useTranslation("auth");
  const options = useRegisterOptions();
  const errorId = error ? "grade-error" : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor="grade">{t("register.grade")}</Label>
      <select
        id="grade"
        aria-invalid={Boolean(error)}
        aria-describedby={errorId}
        disabled={options.isPending}
        className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive"
        {...selectProps}
      >
        <option value="" disabled>
          {t("register.gradePlaceholder")}
        </option>
        {options.data?.grades.map((grade) => (
          <option key={grade} value={grade}>
            {t(`register.gradeOptions.${grade}`)}
          </option>
        ))}
      </select>
      {options.isError && (
        <p role="alert" className="text-sm text-destructive">
          {getProblemMessage(options.error)}
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
