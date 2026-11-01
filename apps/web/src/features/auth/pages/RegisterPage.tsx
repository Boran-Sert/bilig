/**
 * Kullanıcı kayıt formunu gösterir.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { getProblemMessage } from "../../../lib/api/problem";
import { useRegister } from "../api";

const registerSchema = z.object({
  displayName: z.string().trim().min(1, "required"),
  email: z.string().trim().min(1, "required").email("email"),
  password: z
    .string()
    .min(8, "passwordMin")
    .refine((value) => new TextEncoder().encode(value).length <= 72, "passwordMax"),
  grade: z.literal(12),
  explainStyle: z.enum(["SIMPLE", "EXAMPLES", "STEP_BY_STEP"]),
});

type RegisterFormValues = z.infer<typeof registerSchema>;

/**
 * Yeni kullanıcı kayıt formunu yönetir.
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();
  const { t } = useTranslation("auth");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      displayName: "",
      email: "",
      password: "",
      grade: 12,
      explainStyle: "SIMPLE",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await registerMutation.mutateAsync(values);
      navigate("/login", {
        state: { message: t("register.success") },
      });
    } catch {
      // Hata mesajı form üzerinde gösterilir.
    }
  });

  return (
    <section className="mx-auto w-full max-w-md space-y-6 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{t("register.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("register.description")}</p>
      </header>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="displayName" className="text-sm font-medium">
            {t("register.displayName")}
          </label>
          <input
            id="displayName"
            autoComplete="name"
            {...register("displayName")}
            aria-invalid={Boolean(errors.displayName)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {errors.displayName && (
            <p className="text-sm text-destructive">{t("validation.required")}</p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            {t("register.email")}
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            {...register("email")}
            aria-invalid={Boolean(errors.email)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {errors.email && (
            <p className="text-sm text-destructive">{t(`validation.${errors.email.message}`)}</p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium">
            {t("register.password")}
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            {...register("password")}
            aria-invalid={Boolean(errors.password)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {errors.password && (
            <p className="text-sm text-destructive">{t(`validation.${errors.password.message}`)}</p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="grade" className="text-sm font-medium">
            {t("register.grade")}
          </label>
          <select
            id="grade"
            {...register("grade", { valueAsNumber: true })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value={12}>{t("register.gradeOption12")}</option>
          </select>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t("register.explainStyle")}</legend>
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" value="SIMPLE" {...register("explainStyle")} />
              {t("register.explainStyleSimple")}
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" value="EXAMPLES" {...register("explainStyle")} />
              {t("register.explainStyleExamples")}
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" value="STEP_BY_STEP" {...register("explainStyle")} />
              {t("register.explainStyleStepByStep")}
            </label>
          </div>
        </fieldset>

        {registerMutation.isError && (
          <p role="alert" className="text-sm text-destructive">
            {getProblemMessage(registerMutation.error)}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting || registerMutation.isPending}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {registerMutation.isPending ? t("register.submitting") : t("register.submit")}
        </button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {t("register.hasAccount")}{" "}
        <Link to="/login" className="font-medium text-primary underline">
          {t("register.loginLink")}
        </Link>
      </p>
    </section>
  );
}
