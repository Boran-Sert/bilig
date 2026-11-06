/**
 * Bilig logosunu açık veya koyu zeminde gösterir.
 */
import { useTranslation } from "react-i18next";
import lockupInverse from "../assets/brand/logo-lockup-inverse.svg";
import lockup from "../assets/brand/logo-lockup.svg";
import mark from "../assets/brand/logo-mark.svg";

type LogoVariant = "lockup" | "lockupInverse" | "mark";

const LOGO_SOURCES: Record<LogoVariant, string> = {
  lockup,
  lockupInverse,
  mark,
};

interface LogoProps {
  variant?: LogoVariant;
  className?: string;
}

/**
 * Seçilen logo biçimini uygulama adıyla erişilebilir görsel olarak çizer.
 * @param props Logo biçimi ve sınıf adı.
 * @returns Logo görseli.
 */
export default function Logo({ variant = "lockup", className }: LogoProps) {
  const { t } = useTranslation();

  return <img src={LOGO_SOURCES[variant]} alt={t("app.name")} className={className} />;
}
