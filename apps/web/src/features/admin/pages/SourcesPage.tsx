/**
 * İçerik ekibi için PDF kaynak yükleme sayfasını sunar.
 */
import { useState } from "react";
import type { FileRejection } from "react-dropzone";
import { useTranslation } from "react-i18next";
import PageMeta from "../../../components/PageMeta";
import { getProblemMessage } from "../../../lib/api/problem";
import { useMe } from "../../auth/api";
import { useUploadSources } from "../api";
import SourceDropzone from "../components/SourceDropzone";
import UploadResultList from "../components/UploadResultList";

/**
 * Yetkisi sunucuda belirlenen kullanıcıya PDF yükleme ekranını gösterir.
 */
export default function SourcesPage() {
  const { t } = useTranslation("admin");
  const { data: user, isPending: isUserPending } = useMe();
  const uploadMutation = useUploadSources();
  const [rejectedNames, setRejectedNames] = useState<string[]>([]);

  /** PDF'leri yükler, PDF olmayanları adıyla bildirir. */
  function handleDrop(acceptedFiles: File[], rejectedFiles: FileRejection[]) {
    setRejectedNames(rejectedFiles.map((rejection) => rejection.file.name));

    if (acceptedFiles.length > 0) {
      uploadMutation.mutate(acceptedFiles);
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
    </section>
  );
}
