/**
 * Giriş yapmamış ziyaretçilere Bilig'i tanıtan karşılama sayfasını sunar.
 */
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router";
import PageMeta from "../../../components/PageMeta";
import { ROUTES } from "../../../lib/constants";
import { useMe } from "../../auth/api";
import LandingCta from "../components/LandingCta";
import LandingFooter from "../components/LandingFooter";
import LandingHero from "../components/LandingHero";
import LandingInstitutions from "../components/LandingInstitutions";
import LandingNav from "../components/LandingNav";
import LandingStepsSection from "../components/LandingSteps";
import LandingStudents from "../components/LandingStudents";

/**
 * Oturum açıksa panele yönlendirir, değilse tanıtım bölümlerini sırayla gösterir.
 */
export default function LandingPage() {
  const { t } = useTranslation("landing");
  const { data: user, isPending } = useMe();

  if (isPending) {
    return null;
  }

  if (user) {
    return <Navigate to={ROUTES.home} replace />;
  }

  return (
    <div className="min-h-screen bg-background">
      <PageMeta title={t("meta.title")} description={t("meta.description")} />
      <LandingNav />
      <main>
        <LandingHero />
        <LandingStudents />
        <LandingStepsSection />
        <LandingInstitutions />
        <LandingCta />
      </main>
      <LandingFooter />
    </div>
  );
}
