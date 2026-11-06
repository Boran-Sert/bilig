/**
 * Testleri ada, derse ve kazanıma göre ayıklayacak arama alanını gösterir.
 * Backend desteği gelene kadar alanlar devre dışıdır.
 */
import { ChevronDown, Search } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";

const SELECT_CLASS =
  "h-11 w-full appearance-none rounded-xl border border-input bg-card pr-10 pl-4 text-[15px] text-muted-foreground disabled:cursor-not-allowed disabled:opacity-70";

/**
 * Arama kutusunu, ders ve kazanım seçimlerini ve temizle düğmesini yan yana çizer.
 */
export default function TestFilters() {
  const { t } = useTranslation("test");

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm lg:flex-row lg:items-center">
      <div className="relative flex-1">
        <Search
          className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <input
          type="search"
          disabled
          aria-label={t("testList.filters.searchLabel")}
          placeholder={t("testList.filters.searchPlaceholder")}
          className="h-11 w-full rounded-xl border border-input bg-card pr-4 pl-11 text-[15px] placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-70"
        />
      </div>

      {(["subject", "outcome"] as const).map((key) => (
        <div key={key} className="relative lg:w-60">
          <select
            disabled
            defaultValue=""
            aria-label={t(`testList.filters.${key}Label`)}
            className={SELECT_CLASS}
          >
            <option value="">{t(`testList.filters.${key}Placeholder`)}</option>
          </select>
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
        </div>
      ))}

      <Button variant="ghost" disabled className="h-11 px-4 text-info">
        {t("testList.filters.clear")}
      </Button>
    </div>
  );
}
