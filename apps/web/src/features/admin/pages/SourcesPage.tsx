/**
 * İçerik ekibi için PDF kaynak yükleme sayfasını sunar.
 */
import { useState } from "react";
import type { FileRejection } from "react-dropzone";
import { useTranslation } from "react-i18next";
import PageMeta from "../../../components/PageMeta";
import { Label } from "../../../components/ui/label";
import { getProblemMessage } from "../../../lib/api/problem";
import { UPLOAD_SOURCE_KINDS } from "../../../lib/constants";
import { useMe } from "../../auth/api";
import { useSources, useUploadSources } from "../api";
import SourceDropzone from "../components/SourceDropzone";
import SourceList from "../components/SourceList";
import UploadResultList from "../components/UploadResultList";
import type { SourceKind } from "../types";

/**
 * Yetkisi sunucuda belirlenen kullanıcıya PDF yükleme ekranını gösterir.
 */
export default function SourcesPage() {
  const { t } = useTranslation("admin");
  const { data: user, isPending: isUserPending } = useMe();
  const sourcesQuery = useSources(user?.canManageContent === true);
  const uploadMutation = useUploadSources();
  const [rejectedNames, setRejectedNames] = useState<string[]>([]);
  const [kind, setKind] = useState<SourceKind | "">("");
  const [kindMissing, setKindMissing] = useState(false);

  /** PDF'leri seçilen türle yükler, PDF olmayanları adıyla bildirir; tür yoksa yüklemez. */
  function handleDrop(acceptedFiles: File[], rejectedFiles: FileRejection[]) {
    setRejectedNames(rejectedFiles.map((rejection) => rejection.file.name));
    setKindMissing(acceptedFiles.length > 0 && kind === "");

    if (acceptedFiles.length > 0 && kind !== "") {
      uploadMutation.mutate({ files: acceptedFiles, kind });
    }
  }

  if (isUserPending || !user) {
    return null;
  }

  if (!user.canManageContent) {
    return (
      <p role="alert" className="py-12 text-center text-sm font-medium text-destructive">
        {t("sources.errors.accessDenied")}
      </p>
    );
  }

  return (
    <section className="space-y-6">
      <PageMeta title={t("sources.title")} description={t("sources.metaDescription")} />
      <h1 className="text-2xl font-semibold tracking-tight">{t("sources.title")}</h1>

      <div className="max-w-xs space-y-2">
        <Label htmlFor="source-kind">{t("sources.kindLabel")}</Label>
        <select
          id="source-kind"
          value={kind}
          onChange={(event) => {
            setKind(event.target.value as SourceKind);
            setKindMissing(false);
          }}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          <option value="" disabled>
            {t("sources.kindPlaceholder")}
          </option>
          {UPLOAD_SOURCE_KINDS.map((option) => (
            <option key={option} value={option}>
              {t(`sources.kinds.${option}`)}
            </option>
          ))}
        </select>
      </div>

      {kindMissing && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {t("sources.errors.kindRequired")}
        </p>
      )}
      {rejectedNames.length > 0 && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {t("sources.errors.rejectedFiles", { files: rejectedNames.join(", ") })}
        </p>
      )}
      {uploadMutation.isError && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {getProblemMessage(uploadMutation.error)}
        </p>
      )}

      <SourceDropzone isUploading={uploadMutation.isPending} onDrop={handleDrop} />

      {uploadMutation.data?.files && uploadMutation.data.files.length > 0 && (
        <UploadResultList files={uploadMutation.data.files} />
      )}

      {sourcesQuery.isPending && (
        <p className="py-8 text-center text-sm text-muted-foreground">{t("sources.loadingList")}</p>
      )}
      {sourcesQuery.isError && (
        <p role="alert" className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {getProblemMessage(sourcesQuery.error)}
        </p>
      )}
      {sourcesQuery.isSuccess && <SourceList items={sourcesQuery.data.items} />}
    </section>
  );
}
