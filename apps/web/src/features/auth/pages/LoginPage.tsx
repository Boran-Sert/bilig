/**
 * Kullanıcı giriş formunu gösterir.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";
import { useLogin } from "../api";
import { getProblemMessage } from "../../../lib/api/problem";
import { useTranslation } from "react-i18next";

const loginSchema = z.object({
  email: z.string().trim().min(1, "required").email("email"),
  password: z.string().min(1, "required"),
  rememberMe: z.boolean(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

/**
 * Kullanıcı giriş formunu yönetir.
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const successMessage = (location.state as { message?: string } | null)?.message;
  const login = useLogin();
  const { t } = useTranslation("auth");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      await login.mutateAsync(values);
      navigate("/");
    } catch {
      // Hata mesajı form üzerinde gösterilir.
    }
  });

  return (
    <section className="mx-auto w-full max-w-md space-y-6 py-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{t("login.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("login.description")}</p>
      </header>

      {successMessage && (
        <p role="status" className="text-sm text-green-600">
          {successMessage}
        </p>
      )}
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            {t("login.email")}
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
            {t("login.password")}
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            {...register("password")}
            aria-invalid={Boolean(errors.password)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {errors.password && (
            <p className="text-sm text-destructive">{t(`validation.${errors.password.message}`)}</p>
          )}
        </div>

        <div className="space-y-1">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("rememberMe")} />
            {t("login.rememberMe")}
          </label>
          <p className="text-xs text-muted-foreground">{t("login.rememberMeHint")}</p>
        </div>

        {login.isError && (
          <p role="alert" className="text-sm text-destructive">
            {getProblemMessage(login.error)}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting || login.isPending}
          className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {login.isPending ? t("login.submitting") : t("login.submit")}
        </button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {t("login.noAccount")}{" "}
        <Link to="/register" className="font-medium text-primary underline">
          {t("login.registerLink")}
        </Link>
      </p>
    </section>
  );
}
