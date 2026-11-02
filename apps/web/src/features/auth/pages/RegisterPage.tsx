/**
 * Kullanıcı kayıt formunu gösterir.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { z } from "zod";
import FormField from "../../../components/FormField";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getFieldErrors, getProblemMessage } from "../../../lib/api/problem";
import { PASSWORD_MAX_BYTES, PASSWORD_MIN_LENGTH, ROUTES } from "../../../lib/constants";
import { applyServerFieldErrors } from "../../../lib/forms";
import { useRegister } from "../api";

const REGISTER_FIELDS = ["displayName", "email", "password", "consentAccepted"] as const;

/**
 * Sadece parola uzunluğunu anında denetleyen form şemasını üretir.
 * @param messages Parola uzunluğu hata mesajları.
 * @returns Kayıt formu şeması.
 */
function createRegisterSchema(messages: { passwordMin: string; passwordMax: string }) {
  return z.object({
    displayName: z.string(),
    email: z.string(),
    password: z
      .string()
      .min(PASSWORD_MIN_LENGTH, messages.passwordMin)
      .refine(
        (value) => new TextEncoder().encode(value).length <= PASSWORD_MAX_BYTES,
        messages.passwordMax,
      ),
    consentAccepted: z.boolean(),
  });
}

type RegisterFormValues = z.infer<ReturnType<typeof createRegisterSchema>>;

/**
 * Kayıt formunu yönetir; parola dışındaki doğrulamayı sunucuya bırakır.
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegister();
  const { t } = useTranslation("auth");

  const schema = useMemo(
    () =>
      createRegisterSchema({
        passwordMin: t("validation.passwordMin", { min: PASSWORD_MIN_LENGTH }),
        passwordMax: t("validation.passwordMax", { max: PASSWORD_MAX_BYTES }),
      }),
    [t],
  );

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { displayName: "", email: "", password: "", consentAccepted: false },
  });

  const onSubmit = handleSubmit((values) => {
    registerMutation.mutate(values, {
      /** Sunucu oturumu açtığı için ana sayfaya gider. */
      onSuccess: () => navigate(ROUTES.home, { replace: true }),
      /** Sunucunun alan hatalarını forma yazar. */
      onError: (error) => applyServerFieldErrors(error, REGISTER_FIELDS, setError),
    });
  });

  const showGeneralError =
    registerMutation.isError && getFieldErrors(registerMutation.error).length === 0;

  return (
    <section className="mx-auto w-full max-w-md space-y-6 py-10">
      <PageMeta title={t("register.title")} description={t("register.metaDescription")} />
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{t("register.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("register.description")}</p>
      </header>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <FormField
          id="displayName"
          autoComplete="nickname"
          label={t("register.displayName")}
          hint={t("register.displayNameHint")}
          error={errors.displayName?.message}
          {...register("displayName")}
        />
        <FormField
          id="email"
          type="email"
          autoComplete="email"
          label={t("register.email")}
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          id="password"
          type="password"
          autoComplete="new-password"
          label={t("register.password")}
          hint={t("register.passwordHint", { min: PASSWORD_MIN_LENGTH })}
          error={errors.password?.message}
          {...register("password")}
        />

        <div className="space-y-1">
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5"
              aria-invalid={Boolean(errors.consentAccepted)}
              aria-describedby="consentAccepted-hint"
              {...register("consentAccepted")}
            />
            {t("register.consent")}
          </label>
          <p id="consentAccepted-hint" className="text-xs text-muted-foreground">
            {t("register.consentHint")}
          </p>
          {errors.consentAccepted && (
            <p className="text-sm text-destructive">{errors.consentAccepted.message}</p>
          )}
        </div>

        {showGeneralError && (
          <p role="alert" className="text-sm text-destructive">
            {getProblemMessage(registerMutation.error)}
          </p>
        )}

        <Button type="submit" size="lg" className="w-full" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? t("register.submitting") : t("register.submit")}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {t("register.hasAccount")}{" "}
        <Link to={ROUTES.login} className="font-medium text-primary underline">
          {t("register.loginLink")}
        </Link>
      </p>
    </section>
  );
}
