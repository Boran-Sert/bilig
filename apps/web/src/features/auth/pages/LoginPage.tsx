/**
 * Kullanıcı giriş formunu gösterir.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";
import CheckboxField from "../../../components/CheckboxField";
import FormField from "../../../components/FormField";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { getFieldErrors, getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { applyServerFieldErrors } from "../../../lib/forms";
import { useLogin } from "../api";
import AuthLayout from "../components/AuthLayout";
import { getReturnPath } from "../returnPath";
import type { LoginRequest } from "../types";

const LOGIN_FIELDS = ["email", "password"] as const;

/** Giriş formunun şekli; doğrulama sunucudadır. */
const loginSchema = z.object({
  email: z.string(),
  password: z.string(),
  rememberMe: z.boolean(),
}) satisfies z.ZodType<LoginRequest>;

/**
 * Giriş formunu yönetir; doğrulamayı sunucuya bırakır.
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();
  const { t } = useTranslation("auth");

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  const onSubmit = handleSubmit((values) => {
    login.mutate(values, {
      /** Kullanıcıyı geldiği sayfaya geri gönderir. */
      onSuccess: () => navigate(getReturnPath(location.state), { replace: true }),
      /** Sunucunun alan hatalarını forma yazar. */
      onError: (error) => applyServerFieldErrors(error, LOGIN_FIELDS, setError),
    });
  });

  const showGeneralError = login.isError && getFieldErrors(login.error).length === 0;

  return (
    <AuthLayout>
      <section className="space-y-6">
        <PageMeta title={t("login.title")} description={t("login.metaDescription")} />
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">{t("login.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("login.description")}</p>
        </header>

        <form onSubmit={onSubmit} noValidate className="space-y-4">
          <FormField
            id="email"
            type="email"
            autoComplete="email"
            label={t("login.email")}
            error={errors.email?.message}
            {...register("email")}
          />
          <FormField
            id="password"
            type="password"
            autoComplete="current-password"
            label={t("login.password")}
            error={errors.password?.message}
            {...register("password")}
          />

          <CheckboxField
            id="rememberMe"
            label={t("login.rememberMe")}
            hint={t("login.rememberMeHint")}
            {...register("rememberMe")}
          />

          {showGeneralError && (
            <p role="alert" className="text-sm text-destructive">
              {getProblemMessage(login.error)}
            </p>
          )}

          <Button
            type="submit"
            size="lg"
            className="h-12! w-full rounded-xl! text-base!"
            disabled={login.isPending}
          >
            {login.isPending ? t("login.submitting") : t("login.submit")}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          {t("login.noAccount")}{" "}
          <Link to={ROUTES.register} className="font-medium text-info underline">
            {t("login.registerLink")}
          </Link>
        </p>
      </section>
    </AuthLayout>
  );
}
