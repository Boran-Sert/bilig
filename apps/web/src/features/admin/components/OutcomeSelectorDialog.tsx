/**
 * Soru ve paragrafların kazanımlarını güncellemek için arama ve seçim diyaloğu sunar.
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { useOutcomes } from "../api";

interface OutcomeSelectorDialogProps {
  isOpen: boolean;
  initialOutcomeIds: number[];
  onSave: (outcomeIds: number[]) => void;
  onClose: () => void;
}

/**
 * Mevcut kazanımları listeleyip kullanıcının seçmesini sağlar.
 */
export default function OutcomeSelectorDialog({
  isOpen,
  initialOutcomeIds,
  onSave,
  onClose,
}: OutcomeSelectorDialogProps) {
  const { t } = useTranslation("admin");
  const outcomesQuery = useOutcomes();
  const [selectedIds, setSelectedIds] = useState<number[]>(initialOutcomeIds);
  const [search, setSearch] = useState("");

  const filteredOutcomes = useMemo(() => {
    const list = outcomesQuery.data ?? [];
    if (!search.trim()) return list;
    const lower = search.trim().toLocaleLowerCase("tr-TR");
    return list.filter(
      (item) =>
        item.code.toLocaleLowerCase("tr-TR").includes(lower) ||
        item.title.toLocaleLowerCase("tr-TR").includes(lower),
    );
  }, [outcomesQuery.data, search]);

  if (!isOpen) return null;

  /** Seçim durumunu tersine çevirir. */
  function toggleOutcome(id: number) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg bg-card p-5 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 className="text-base font-semibold">{t("review.outcomes.editTitle")}</h2>

        <div className="my-3">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("review.outcomes.searchPlaceholder")}
          />
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto py-2">
          {filteredOutcomes.map((outcome) => {
            const isChecked = selectedIds.includes(outcome.id);
            return (
              <label
                key={outcome.id}
                className="flex cursor-pointer items-start gap-2 rounded p-2 text-xs hover:bg-muted"
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => toggleOutcome(outcome.id)}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-semibold text-foreground">{outcome.code} </span>
                  <span className="text-muted-foreground">{outcome.title}</span>
                </div>
              </label>
            );
          })}
          {filteredOutcomes.length === 0 && (
            <p className="py-4 text-center text-xs text-muted-foreground">
              {t("review.outcomes.none")}
            </p>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2 border-t pt-3">
          <Button variant="outline" size="sm" onClick={onClose}>
            {t("review.outcomes.cancel")}
          </Button>
          <Button size="sm" disabled={selectedIds.length === 0} onClick={() => onSave(selectedIds)}>
            {t("review.outcomes.save")}
          </Button>
        </div>
      </div>
    </div>
  );
}
