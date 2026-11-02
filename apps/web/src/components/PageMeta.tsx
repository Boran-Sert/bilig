/**
 * Sayfanın tarayıcı başlığını ve açıklama meta etiketini yazar.
 */
import { useTranslation } from "react-i18next";

interface PageMetaProps {
  title: string;
  description: string;
}

/**
 * React 19'un head'e taşıdığı title ve description etiketlerini üretir.
 * @param props Sayfa başlığı ve açıklaması.
 * @returns Başlık ve meta etiketleri.
 */
export default function PageMeta({ title, description }: PageMetaProps) {
  const { t } = useTranslation();

  return (
    <>
      <title>{t("app.pageTitle", { page: title })}</title>
      <meta name="description" content={description} />
    </>
  );
}
