/**
 * İçerik ekibi için PDF kaynak yükleme sayfasını sunar.
 */
import { useCallback, useState } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { Button } from "../../../components/ui/button";
import { useMe } from "../../auth/api";
import { getProblemMessage } from "../../../lib/api/problem";
import { ROUTES } from "../../../lib/constants";
import { useUploadSources } from "../api";

const REQUIRED_ROLE = "CONTENT_ADMIN";

/**
 * İçerik yöneticisinin PDF dosyalarını sürükleyip yükleyebileceği sayfayı oluşturur.
 */
export default function SourcesPage() {
  const { t } = useTranslation("admin");
  const { data: user, isPending: isUserPending } = useMe();
  const uploadMutation = useUploadSources();
  const [clientError, setClientError] = useState<string | null>(null);

  /** Geçerli PDF dosyalarını sunucuya gönderir. */
  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setClientError(null);

      if (rejectedFiles.length > 0) {
        setClientError(t("sources.errors.invalidFileType"));
        return;
      }

      const validPdfs = acceptedFiles.filter(
        (file) => file.type === "application/pdf" && file.name.toLowerCase().endsWith(".pdf"),
      );

      if (validPdfs.length === 0) {
        if (acceptedFiles.length > 0) {
          setClientError(t("sources.errors.invalidFileType"));
        }
        return;
      }

      uploadMutation.mutate(validPdfs);
    },
    [t, uploadMutation],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
    noClick: true,
    disabled: uploadMutation.isPending,
  });

  if (isUserPending) {
    return null;
  }

  if (!user) {
    return <Navigate to={ROUTES.login} replace />;
  }

  if (user.role !== REQUIRED_ROLE) {
    return (
      <section className="py-12 text-center">
        <p role="alert" className="text-sm font-medium text-destructive">
          {t("sources.errors.accessDenied")}
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageMeta title={t("sources.title")} description={t("sources.metaDescription")} />

      <div className="flex items-baseline gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{t("sources.title")}</h1>
        <span className="text-sm text-muted-foreground">{t("sources.programTag")}</span>
      </div>

      {(clientError || uploadMutation.isError) && (
        <div
          role="alert"
          className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {clientError || getProblemMessage(uploadMutation.error)}
        </div>
      )}

      <div
        {...getRootProps()}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-border hover:border-muted-foreground/50"
        } ${uploadMutation.isPending ? "pointer-events-none opacity-60" : ""}`}
      >
        <input {...getInputProps()} />
        <p className="text-base font-semibold">{t("sources.dropTitle")}</p>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">
          {t("sources.dropDescription")}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={open}
          disabled={uploadMutation.isPending}
        >
          {uploadMutation.isPending ? t("sources.status.uploading") : t("sources.selectButton")}
        </Button>
      </div>

      {uploadMutation.data?.files && uploadMutation.data.files.length > 0 && (
        <div className="space-y-3 pt-4">
          <div className="grid grid-cols-12 border-b border-border pb-2 text-xs font-semibold text-muted-foreground">
            <span className="col-span-6">{t("sources.table.file")}</span>
            <span className="col-span-3">{t("sources.table.status")}</span>
            <span className="col-span-3">{t("sources.table.result")}</span>
          </div>

          <div className="divide-y divide-border">
            {uploadMutation.data.files.map((file, index) => (
              <div
                key={file.sourceId ?? index}
                className="grid grid-cols-12 items-center py-3 text-sm"
              >
                <span className="col-span-6 font-medium">{file.fileName}</span>
                <span className="col-span-3 text-muted-foreground">
                  {t("sources.status.uploaded")}
                </span>
                <span className="col-span-3">
                  {file.duplicate ? (
                    <span className="inline-flex rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
                      {t("sources.status.duplicate")}
                    </span>
                  ) : (
                    <span className="inline-flex rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                      {t("sources.status.uploaded")}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
