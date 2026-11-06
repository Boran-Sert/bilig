/**
 * Karşılama sayfasının alt bilgisini, bağlantı sütunlarını ve iletişim bilgilerini sunar.
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import Logo from "../../../components/Logo";
import { ROUTES } from "../../../lib/constants";

interface FooterLink {
  key: string;
  to?: string;
  anchor?: string;
}

interface FooterColumn {
  group: "product" | "institutions" | "legal";
  links: FooterLink[];
}

const COLUMNS: FooterColumn[] = [
  {
    group: "product",
    links: [
      { key: "students", anchor: "#ogrenciler" },
      { key: "howItWorks", anchor: "#nasil-calisir" },
      { key: "login", to: ROUTES.login },
      { key: "register", to: ROUTES.register },
    ],
  },
  {
    group: "institutions",
    links: [
      { key: "forInstitutions", anchor: "#kurumlar" },
      { key: "integration" },
      { key: "contact" },
    ],
  },
  {
    group: "legal",
    links: [{ key: "privacy" }, { key: "terms" }, { key: "kvkk" }],
  },
];

const SOCIAL_KEYS = ["linkedin", "instagram", "youtube"] as const;

/**
 * Marka açıklamasını, üç bağlantı sütununu ve telif satırını gösterir.
 */
export default function LandingFooter() {
  const { t } = useTranslation("landing");

  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto max-w-6xl space-y-10 px-4 py-14 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[320px_1fr]">
          <div className="space-y-4">
            <Logo className="h-9 w-auto" />
            <p className="text-sm text-foreground">{t("footer.description")}</p>
            <dl className="space-y-1 text-sm">
              <div className="flex gap-3">
                <dt className="w-16 text-muted-foreground">{t("footer.emailLabel")}</dt>
                <dd className="text-heading">{t("footer.email")}</dd>
              </div>
              <div className="flex gap-3">
                <dt className="w-16 text-muted-foreground">{t("footer.phoneLabel")}</dt>
                <dd className="text-heading">{t("footer.phone")}</dd>
              </div>
            </dl>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {COLUMNS.map((column) => (
              <div key={column.group} className="space-y-3">
                <h3 className="text-sm font-semibold text-heading">
                  {t(`footer.${column.group}.title`)}
                </h3>
                <ul className="space-y-2 text-foreground">
                  {column.links.map((link) => (
                    <li key={link.key}>
                      {link.to ? (
                        <Link to={link.to} className="hover:text-info">
                          {t(`footer.${column.group}.${link.key}`)}
                        </Link>
                      ) : link.anchor ? (
                        <a href={link.anchor} className="hover:text-info">
                          {t(`footer.${column.group}.${link.key}`)}
                        </a>
                      ) : (
                        <span>{t(`footer.${column.group}.${link.key}`)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-border pt-6 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>{t("footer.copyright")}</p>
          <ul className="flex gap-6 text-foreground">
            {SOCIAL_KEYS.map((key) => (
              <li key={key}>{t(`footer.social.${key}`)}</li>
            ))}
          </ul>
        </div>
      </div>
    </footer>
  );
}
